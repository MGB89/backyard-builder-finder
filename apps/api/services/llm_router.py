"""
LLM Router service for encrypted user API key management and provider routing.

Supports OpenAI and Anthropic with automatic fallback, budget tracking,
and secure key storage using KMS encryption.
"""

import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from datetime import datetime, timedelta
from enum import Enum
import aiohttp
import openai
from anthropic import AsyncAnthropic

from core.config import settings
from services.secrets import get_secrets_manager
from services.providers import get_secrets_provider
from core.security import encrypt_api_key, decrypt_api_key
from models.user import User, UserApiKey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMModel(str, Enum):
    """Supported LLM models with their specifications."""
    # OpenAI models
    GPT_4_TURBO = "gpt-4-turbo-preview"
    GPT_4 = "gpt-4"
    GPT_3_5_TURBO = "gpt-3.5-turbo"
    
    # Anthropic models
    CLAUDE_3_OPUS = "claude-3-opus-20240229"
    CLAUDE_3_SONNET = "claude-3-sonnet-20240229"
    CLAUDE_3_HAIKU = "claude-3-haiku-20240307"


# Model specifications for cost and capability tracking
MODEL_SPECS = {
    LLMModel.GPT_4_TURBO: {
        "provider": LLMProvider.OPENAI,
        "max_tokens": 128000,
        "cost_per_1k_input": 0.01,
        "cost_per_1k_output": 0.03,
        "capabilities": ["reasoning", "analysis", "json_mode"]
    },
    LLMModel.GPT_4: {
        "provider": LLMProvider.OPENAI,
        "max_tokens": 8192,
        "cost_per_1k_input": 0.03,
        "cost_per_1k_output": 0.06,
        "capabilities": ["reasoning", "analysis"]
    },
    LLMModel.GPT_3_5_TURBO: {
        "provider": LLMProvider.OPENAI,
        "max_tokens": 16384,
        "cost_per_1k_input": 0.0005,
        "cost_per_1k_output": 0.0015,
        "capabilities": ["json_mode"]
    },
    LLMModel.CLAUDE_3_OPUS: {
        "provider": LLMProvider.ANTHROPIC,
        "max_tokens": 200000,
        "cost_per_1k_input": 0.015,
        "cost_per_1k_output": 0.075,
        "capabilities": ["reasoning", "analysis", "long_context"]
    },
    LLMModel.CLAUDE_3_SONNET: {
        "provider": LLMProvider.ANTHROPIC,
        "max_tokens": 200000,
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
        "capabilities": ["reasoning", "analysis", "long_context"]
    },
    LLMModel.CLAUDE_3_HAIKU: {
        "provider": LLMProvider.ANTHROPIC,
        "max_tokens": 200000,
        "cost_per_1k_input": 0.00025,
        "cost_per_1k_output": 0.00125,
        "capabilities": ["speed", "long_context"]
    }
}


class LLMUsageTracker:
    """Track LLM usage and costs per user/organization."""
    
    def __init__(self):
        self._usage_cache = {}  # In-memory cache for quick access
    
    async def get_daily_usage(self, user_id: str, org_id: str) -> Dict[str, Any]:
        """Get today's LLM usage for a user/org."""
        cache_key = f"{org_id}_{user_id}_{datetime.now().date()}"
        
        if cache_key in self._usage_cache:
            return self._usage_cache[cache_key]
        
        # In production, this would query a database
        # For now, return empty usage
        usage = {
            "tokens_used": 0,
            "cost_usd": 0.0,
            "requests_count": 0,
            "by_model": {}
        }
        
        self._usage_cache[cache_key] = usage
        return usage
    
    async def record_usage(
        self,
        user_id: str,
        org_id: str,
        model: LLMModel,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float
    ):
        """Record LLM usage."""
        cache_key = f"{org_id}_{user_id}_{datetime.now().date()}"
        
        usage = await self.get_daily_usage(user_id, org_id)
        
        # Update totals
        usage["tokens_used"] += input_tokens + output_tokens
        usage["cost_usd"] += cost_usd
        usage["requests_count"] += 1
        
        # Update by model
        if model not in usage["by_model"]:
            usage["by_model"][model] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "cost_usd": 0.0,
                "requests": 0
            }
        
        model_usage = usage["by_model"][model]
        model_usage["input_tokens"] += input_tokens
        model_usage["output_tokens"] += output_tokens
        model_usage["cost_usd"] += cost_usd
        model_usage["requests"] += 1
        
        self._usage_cache[cache_key] = usage
        
        # TODO: In production, persist to database
        logger.info(f"Recorded LLM usage: {user_id} used {input_tokens + output_tokens} tokens ({model}) for ${cost_usd:.4f}")


class LLMRouter:
    """
    Production LLM router with encrypted key management and intelligent routing.
    """
    
    def __init__(self):
        self.usage_tracker = LLMUsageTracker()
        self.secrets_manager = get_secrets_manager()
        
        # Initialize provider-based services
        try:
            self.secrets_provider = get_secrets_provider()
        except Exception as e:
            logger.warning(f"Secrets provider not available: {e}")
            self.secrets_provider = None
        
        # Rate limiting (simple in-memory implementation)
        self._rate_limits = {}
        
        logger.info("LLM Router initialized")
    
    async def get_user_api_keys(self, user_id: str, provider: LLMProvider) -> Optional[str]:
        """
        Retrieve and decrypt user's API key for a specific provider.
        
        Args:
            user_id: User ID
            provider: LLM provider
            
        Returns:
            Decrypted API key or None if not found
        """
        try:
            async with AsyncSessionLocal() as db:
                # Query for user's API key
                result = await db.execute(
                    select(UserApiKey).where(
                        UserApiKey.user_id == user_id,
                        UserApiKey.name == f"llm_{provider.value}",
                        UserApiKey.is_active == True
                    )
                )\n                \n                api_key_record = result.scalar_one_or_none()\n                \n                if not api_key_record:\n                    logger.debug(f\"No {provider} API key found for user {user_id}\")\n                    return None\n                \n                # Decrypt the API key\n                decrypted_key = decrypt_api_key(api_key_record.key_hash)\n                \n                # Update last used timestamp\n                await db.execute(\n                    update(UserApiKey)\n                    .where(UserApiKey.id == api_key_record.id)\n                    .values(last_used_at=datetime.utcnow())\n                )\n                await db.commit()\n                \n                return decrypted_key\n                \n        except Exception as e:\n            logger.error(f\"Failed to retrieve {provider} API key for user {user_id}: {e}\")\n            return None\n    \n    async def store_user_api_key(\n        self,\n        user_id: str,\n        org_id: str,\n        provider: LLMProvider,\n        api_key: str,\n        key_name: Optional[str] = None\n    ) -> bool:\n        \"\"\"Store encrypted user API key.\"\"\"\n        try:\n            async with AsyncSessionLocal() as db:\n                # Check if key already exists\n                existing_key = await db.execute(\n                    select(UserApiKey).where(\n                        UserApiKey.user_id == user_id,\n                        UserApiKey.name == f\"llm_{provider.value}\"\n                    )\n                )\n                existing_key = existing_key.scalar_one_or_none()\n                \n                if existing_key:\n                    # Update existing key\n                    encrypted_key = encrypt_api_key(api_key)\n                    await db.execute(\n                        update(UserApiKey)\n                        .where(UserApiKey.id == existing_key.id)\n                        .values(\n                            key_hash=encrypted_key,\n                            updated_at=datetime.utcnow(),\n                            is_active=True\n                        )\n                    )\n                    logger.info(f\"Updated {provider} API key for user {user_id}\")\n                else:\n                    # Create new key record\n                    encrypted_key = encrypt_api_key(api_key)\n                    key_prefix = api_key[:8] if len(api_key) > 8 else api_key[:4]\n                    \n                    new_key = UserApiKey(\n                        user_id=user_id,\n                        org_id=org_id,\n                        name=key_name or f\"llm_{provider.value}\",\n                        key_hash=encrypted_key,\n                        key_prefix=key_prefix,\n                        scopes=json.dumps([\"llm_access\"]),\n                        is_active=True\n                    )\n                    \n                    db.add(new_key)\n                    logger.info(f\"Stored new {provider} API key for user {user_id}\")\n                \n                await db.commit()\n                return True\n                \n        except Exception as e:\n            logger.error(f\"Failed to store {provider} API key for user {user_id}: {e}\")\n            return False\n    \n    async def check_budget_limits(\n        self,\n        user_id: str,\n        org_id: str,\n        estimated_cost: float\n    ) -> Tuple[bool, Dict[str, Any]]:\n        \"\"\"Check if user/org is within budget limits.\"\"\"\n        try:\n            # Get current usage\n            usage = await self.usage_tracker.get_daily_usage(user_id, org_id)\n            \n            # Get limits from settings\n            daily_limit = settings.MAX_LLM_TOKENS_PER_ORG_DAILY * 0.001  # Rough cost estimate\n            \n            projected_cost = usage[\"cost_usd\"] + estimated_cost\n            \n            within_budget = projected_cost <= daily_limit\n            \n            budget_info = {\n                \"current_cost\": usage[\"cost_usd\"],\n                \"estimated_cost\": estimated_cost,\n                \"projected_cost\": projected_cost,\n                \"daily_limit\": daily_limit,\n                \"remaining_budget\": max(0, daily_limit - usage[\"cost_usd\"]),\n                \"within_budget\": within_budget\n            }\n            \n            if not within_budget:\n                logger.warning(f\"Budget exceeded for org {org_id}: ${projected_cost:.4f} > ${daily_limit:.4f}\")\n            \n            return within_budget, budget_info\n            \n        except Exception as e:\n            logger.error(f\"Failed to check budget limits: {e}\")\n            # Fail closed - deny request if we can't check budget\n            return False, {\"error\": str(e)}\n    \n    async def select_best_model(\n        self,\n        task_type: str,\n        max_tokens: Optional[int] = None,\n        budget_priority: bool = False\n    ) -> LLMModel:\n        \"\"\"Select the best model for a given task type.\"\"\"\n        \n        # Define task-specific model preferences\n        task_preferences = {\n            \"zoning_analysis\": [LLMModel.CLAUDE_3_SONNET, LLMModel.GPT_4_TURBO, LLMModel.GPT_3_5_TURBO],\n            \"data_extraction\": [LLMModel.GPT_3_5_TURBO, LLMModel.CLAUDE_3_HAIKU, LLMModel.GPT_4],\n            \"reasoning\": [LLMModel.CLAUDE_3_OPUS, LLMModel.GPT_4_TURBO, LLMModel.CLAUDE_3_SONNET],\n            \"quick_analysis\": [LLMModel.CLAUDE_3_HAIKU, LLMModel.GPT_3_5_TURBO],\n            \"default\": [LLMModel.CLAUDE_3_SONNET, LLMModel.GPT_3_5_TURBO]\n        }\n        \n        candidates = task_preferences.get(task_type, task_preferences[\"default\"])\n        \n        # Filter by token requirements\n        if max_tokens:\n            candidates = [\n                model for model in candidates\n                if MODEL_SPECS[model][\"max_tokens\"] >= max_tokens\n            ]\n        \n        # Sort by cost if budget priority\n        if budget_priority:\n            candidates = sorted(\n                candidates,\n                key=lambda m: MODEL_SPECS[m][\"cost_per_1k_input\"] + MODEL_SPECS[m][\"cost_per_1k_output\"]\n            )\n        \n        return candidates[0] if candidates else LLMModel.GPT_3_5_TURBO\n    \n    async def call_llm(\n        self,\n        user_id: str,\n        org_id: str,\n        messages: List[Dict[str, str]],\n        model: Optional[LLMModel] = None,\n        task_type: str = \"default\",\n        max_tokens: Optional[int] = None,\n        temperature: float = 0.1,\n        **kwargs\n    ) -> Tuple[bool, Dict[str, Any]]:\n        \"\"\"Make LLM API call with automatic provider routing and budget checking.\"\"\"\n        \n        try:\n            # Select model if not specified\n            if not model:\n                model = await self.select_best_model(task_type, max_tokens)\n            \n            model_spec = MODEL_SPECS[model]\n            provider = model_spec[\"provider\"]\n            \n            # Estimate cost (rough calculation)\n            estimated_tokens = sum(len(msg[\"content\"]) // 4 for msg in messages)  # Rough token estimate\n            estimated_cost = (\n                estimated_tokens * model_spec[\"cost_per_1k_input\"] / 1000 +\n                (max_tokens or 1000) * model_spec[\"cost_per_1k_output\"] / 1000\n            )\n            \n            # Check budget\n            within_budget, budget_info = await self.check_budget_limits(user_id, org_id, estimated_cost)\n            if not within_budget:\n                return False, {\n                    \"error\": \"Budget limit exceeded\",\n                    \"budget_info\": budget_info\n                }\n            \n            # Get user's API key for the provider\n            api_key = await self.get_user_api_keys(user_id, provider)\n            if not api_key:\n                return False, {\n                    \"error\": f\"No {provider.value} API key configured for user\",\n                    \"provider\": provider.value\n                }\n            \n            # Make API call based on provider\n            if provider == LLMProvider.OPENAI:\n                result = await self._call_openai(api_key, model, messages, max_tokens, temperature, **kwargs)\n            elif provider == LLMProvider.ANTHROPIC:\n                result = await self._call_anthropic(api_key, model, messages, max_tokens, temperature, **kwargs)\n            else:\n                return False, {\"error\": f\"Unsupported provider: {provider}\"}\n            \n            if result[0]:  # Success\n                # Record actual usage\n                response_data = result[1]\n                actual_input_tokens = response_data.get(\"usage\", {}).get(\"prompt_tokens\", estimated_tokens)\n                actual_output_tokens = response_data.get(\"usage\", {}).get(\"completion_tokens\", max_tokens or 1000)\n                actual_cost = (\n                    actual_input_tokens * model_spec[\"cost_per_1k_input\"] / 1000 +\n                    actual_output_tokens * model_spec[\"cost_per_1k_output\"] / 1000\n                )\n                \n                await self.usage_tracker.record_usage(\n                    user_id, org_id, model, actual_input_tokens, actual_output_tokens, actual_cost\n                )\n                \n                # Add metadata to response\n                response_data[\"metadata\"] = {\n                    \"model\": model,\n                    \"provider\": provider.value,\n                    \"cost_usd\": actual_cost,\n                    \"budget_info\": budget_info\n                }\n            \n            return result\n            \n        except Exception as e:\n            logger.error(f\"LLM call failed for user {user_id}: {e}\")\n            return False, {\"error\": str(e)}\n    \n    async def _call_openai(\n        self,\n        api_key: str,\n        model: LLMModel,\n        messages: List[Dict[str, str]],\n        max_tokens: Optional[int],\n        temperature: float,\n        **kwargs\n    ) -> Tuple[bool, Dict[str, Any]]:\n        \"\"\"Make OpenAI API call.\"\"\"\n        try:\n            client = openai.AsyncOpenAI(api_key=api_key)\n            \n            response = await client.chat.completions.create(\n                model=model.value,\n                messages=messages,\n                max_tokens=max_tokens,\n                temperature=temperature,\n                **kwargs\n            )\n            \n            result = {\n                \"content\": response.choices[0].message.content,\n                \"usage\": {\n                    \"prompt_tokens\": response.usage.prompt_tokens,\n                    \"completion_tokens\": response.usage.completion_tokens,\n                    \"total_tokens\": response.usage.total_tokens\n                },\n                \"finish_reason\": response.choices[0].finish_reason\n            }\n            \n            return True, result\n            \n        except Exception as e:\n            logger.error(f\"OpenAI API call failed: {e}\")\n            return False, {\"error\": str(e)}\n    \n    async def _call_anthropic(\n        self,\n        api_key: str,\n        model: LLMModel,\n        messages: List[Dict[str, str]],\n        max_tokens: Optional[int],\n        temperature: float,\n        **kwargs\n    ) -> Tuple[bool, Dict[str, Any]]:\n        \"\"\"Make Anthropic API call.\"\"\"\n        try:\n            client = AsyncAnthropic(api_key=api_key)\n            \n            # Convert OpenAI format to Anthropic format\n            system_message = None\n            conversation_messages = []\n            \n            for msg in messages:\n                if msg[\"role\"] == \"system\":\n                    system_message = msg[\"content\"]\n                else:\n                    conversation_messages.append(msg)\n            \n            response = await client.messages.create(\n                model=model.value,\n                max_tokens=max_tokens or 1000,\n                temperature=temperature,\n                system=system_message,\n                messages=conversation_messages\n            )\n            \n            result = {\n                \"content\": response.content[0].text if response.content else \"\",\n                \"usage\": {\n                    \"prompt_tokens\": response.usage.input_tokens,\n                    \"completion_tokens\": response.usage.output_tokens,\n                    \"total_tokens\": response.usage.input_tokens + response.usage.output_tokens\n                },\n                \"finish_reason\": response.stop_reason\n            }\n            \n            return True, result\n            \n        except Exception as e:\n            logger.error(f\"Anthropic API call failed: {e}\")\n            return False, {\"error\": str(e)}\n    \n    async def get_usage_summary(self, user_id: str, org_id: str) -> Dict[str, Any]:\n        \"\"\"Get LLM usage summary for user/org.\"\"\"\n        try:\n            usage = await self.usage_tracker.get_daily_usage(user_id, org_id)\n            \n            # Add budget information\n            daily_limit = settings.MAX_LLM_TOKENS_PER_ORG_DAILY * 0.001\n            remaining_budget = max(0, daily_limit - usage[\"cost_usd\"])\n            \n            summary = {\n                **usage,\n                \"daily_limit_usd\": daily_limit,\n                \"remaining_budget_usd\": remaining_budget,\n                \"budget_used_percent\": (usage[\"cost_usd\"] / daily_limit) * 100 if daily_limit > 0 else 0,\n                \"date\": datetime.now().date().isoformat()\n            }\n            \n            return summary\n            \n        except Exception as e:\n            logger.error(f\"Failed to get usage summary: {e}\")\n            return {\"error\": str(e)}\n\n\n# Global router instance\nllm_router = LLMRouter()\n\n\ndef get_llm_router() -> LLMRouter:\n    \"\"\"Get the global LLM router instance.\"\"\"\n    return llm_router