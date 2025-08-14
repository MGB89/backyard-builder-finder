/**
 * Calculation utilities for property assessment data
 */

import type { ComparableSale } from '../types/index.js';

// Basic mathematical utilities
export function roundToDecimalPlaces(value: number, decimals: number): number {
  const factor = Math.pow(10, decimals);
  return Math.round((value + Number.EPSILON) * factor) / factor;
}

export function calculatePercentage(part: number, whole: number): number {
  if (whole === 0) return 0;
  return (part / whole) * 100;
}

export function calculatePercentageChange(oldValue: number, newValue: number): number {
  if (oldValue === 0) return newValue > 0 ? 100 : 0;
  return ((newValue - oldValue) / oldValue) * 100;
}

export function calculateCompoundAnnualGrowthRate(
  initialValue: number,
  finalValue: number,
  years: number
): number {
  if (initialValue <= 0 || finalValue <= 0 || years <= 0) return 0;
  return (Math.pow(finalValue / initialValue, 1 / years) - 1) * 100;
}

// Property value calculations
export function calculateTotalValue(landValue: number, improvementValue: number): number {
  return landValue + improvementValue;
}

export function calculateAssessedValue(
  totalValue: number,
  exemptions: Array<{ exemptionAmount?: number; exemptionPercentage?: number }>
): number {
  let assessedValue = totalValue;
  
  exemptions.forEach(exemption => {
    if (exemption.exemptionAmount) {
      assessedValue -= exemption.exemptionAmount;
    } else if (exemption.exemptionPercentage) {
      assessedValue -= (totalValue * exemption.exemptionPercentage / 100);
    }
  });
  
  return Math.max(0, assessedValue);
}

export function calculateTaxAmount(assessedValue: number, taxRate: number): number {
  return assessedValue * (taxRate / 100);
}

export function calculateMillageRate(taxAmount: number, assessedValue: number): number {
  if (assessedValue === 0) return 0;
  return (taxAmount / assessedValue) * 1000; // Convert to mills
}

// Depreciation calculations
export function calculateStraightLineDepreciation(
  originalCost: number,
  salvageValue: number,
  usefulLife: number,
  age: number
): number {
  const annualDepreciation = (originalCost - salvageValue) / usefulLife;
  const totalDepreciation = annualDepreciation * Math.min(age, usefulLife);
  return Math.max(0, Math.min(totalDepreciation, originalCost - salvageValue));
}

export function calculateAcceleratedDepreciation(
  originalCost: number,
  salvageValue: number,
  usefulLife: number,
  age: number,
  method: 'double-declining' | 'sum-of-years'
): number {
  if (method === 'double-declining') {
    const rate = 2 / usefulLife;
    let bookValue = originalCost;
    
    for (let year = 1; year <= age && year <= usefulLife; year++) {
      const yearlyDepreciation = bookValue * rate;
      const maxDepreciation = bookValue - salvageValue;
      bookValue -= Math.min(yearlyDepreciation, maxDepreciation);
    }
    
    return originalCost - bookValue;
  } else if (method === 'sum-of-years') {
    const sumOfYears = (usefulLife * (usefulLife + 1)) / 2;
    let totalDepreciation = 0;
    
    for (let year = 1; year <= age && year <= usefulLife; year++) {
      const fraction = (usefulLife - year + 1) / sumOfYears;
      totalDepreciation += (originalCost - salvageValue) * fraction;
    }
    
    return totalDepreciation;
  }
  
  return 0;
}

export function calculateEffectiveAge(
  actualAge: number,
  condition: string,
  quality: string
): number {
  let multiplier = 1.0;
  
  // Condition adjustments
  switch (condition.toLowerCase()) {
    case 'excellent':
      multiplier *= 0.8;
      break;
    case 'good':
      multiplier *= 0.9;
      break;
    case 'average':
      multiplier *= 1.0;
      break;
    case 'fair':
      multiplier *= 1.2;
      break;
    case 'poor':
      multiplier *= 1.5;
      break;
  }
  
  // Quality adjustments
  switch (quality.toLowerCase()) {
    case 'luxury':
      multiplier *= 0.9;
      break;
    case 'good':
      multiplier *= 0.95;
      break;
    case 'average':
      multiplier *= 1.0;
      break;
    case 'economy':
      multiplier *= 1.1;
      break;
  }
  
  return actualAge * multiplier;
}

// Cost approach calculations
export function calculateReplacementCost(
  squareFootage: number,
  costPerSquareFoot: number,
  adjustmentFactors?: {
    location?: number;
    quality?: number;
    features?: number;
  }
): number {
  let baseCost = squareFootage * costPerSquareFoot;
  
  if (adjustmentFactors) {
    if (adjustmentFactors.location) {
      baseCost *= (1 + adjustmentFactors.location / 100);
    }
    if (adjustmentFactors.quality) {
      baseCost *= (1 + adjustmentFactors.quality / 100);
    }
    if (adjustmentFactors.features) {
      baseCost *= (1 + adjustmentFactors.features / 100);
    }
  }
  
  return baseCost;
}

export function calculateCostApproachValue(
  landValue: number,
  replacementCost: number,
  depreciation: number
): number {
  const depreciatedImprovementValue = replacementCost - depreciation;
  return landValue + Math.max(0, depreciatedImprovementValue);
}

// Sales comparison approach calculations
export function calculateSaleAdjustment(
  salePrice: number,
  adjustments: Array<{ factor: string; adjustment: number }>
): number {
  let adjustedPrice = salePrice;
  
  adjustments.forEach(adj => {
    adjustedPrice += adj.adjustment;
  });
  
  return adjustedPrice;
}

export function calculateTimeAdjustment(
  salePrice: number,
  saleDate: string,
  valuationDate: string,
  annualAppreciationRate: number
): number {
  const saleDateObj = new Date(saleDate);
  const valuationDateObj = new Date(valuationDate);
  const monthsDifference = (valuationDateObj.getTime() - saleDateObj.getTime()) / (1000 * 60 * 60 * 24 * 30.44);
  const yearsDifference = monthsDifference / 12;
  
  return salePrice * Math.pow(1 + annualAppreciationRate / 100, yearsDifference);
}

export function calculateSalesComparisonValue(
  comparableSales: ComparableSale[],
  weights?: number[]
): number {
  if (comparableSales.length === 0) return 0;
  
  const validSales = comparableSales.filter(sale => sale.adjustedPrice && sale.adjustedPrice > 0);
  if (validSales.length === 0) return 0;
  
  if (weights && weights.length === validSales.length) {
    const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
    const weightedSum = validSales.reduce((sum, sale, index) => 
      sum + (sale.adjustedPrice! * weights[index]), 0
    );
    return weightedSum / totalWeight;
  } else {
    // Simple average
    const sum = validSales.reduce((sum, sale) => sum + sale.adjustedPrice!, 0);
    return sum / validSales.length;
  }
}

// Income approach calculations
export function calculateGrossRentMultiplier(salePrice: number, annualRent: number): number {
  if (annualRent === 0) return 0;
  return salePrice / annualRent;
}

export function calculateCapitalizationRate(netIncome: number, value: number): number {
  if (value === 0) return 0;
  return (netIncome / value) * 100;
}

export function calculateIncomeApproachValue(
  grossIncome: number,
  vacancyRate: number,
  operatingExpenses: number,
  capitalizationRate: number
): number {
  const effectiveGrossIncome = grossIncome * (1 - vacancyRate / 100);
  const netOperatingIncome = effectiveGrossIncome - operatingExpenses;
  
  if (capitalizationRate === 0) return 0;
  return netOperatingIncome / (capitalizationRate / 100);
}

export function calculateCashFlowValue(
  annualCashFlows: number[],
  discountRate: number,
  terminalValue?: number
): number {
  let presentValue = 0;
  
  annualCashFlows.forEach((cashFlow, year) => {
    presentValue += cashFlow / Math.pow(1 + discountRate / 100, year + 1);
  });
  
  if (terminalValue) {
    const terminalPresentValue = terminalValue / Math.pow(1 + discountRate / 100, annualCashFlows.length);
    presentValue += terminalPresentValue;
  }
  
  return presentValue;
}

// Land value calculations
export function calculateLandValuePerSquareFoot(
  totalLandValue: number,
  landArea: number
): number {
  if (landArea === 0) return 0;
  return totalLandValue / landArea;
}

export function calculateLandValuePerAcre(
  totalLandValue: number,
  landArea: number
): number {
  if (landArea === 0) return 0;
  const acres = landArea / 43560; // Convert square feet to acres
  return totalLandValue / acres;
}

export function calculateResidualLandValue(
  totalValue: number,
  improvementValue: number
): number {
  return Math.max(0, totalValue - improvementValue);
}

// Statistical calculations for market analysis
export function calculateMedian(values: number[]): number {
  if (values.length === 0) return 0;
  
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  
  if (sorted.length % 2 === 0) {
    return (sorted[middle - 1] + sorted[middle]) / 2;
  } else {
    return sorted[middle];
  }
}

export function calculateMean(values: number[]): number {
  if (values.length === 0) return 0;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

export function calculateStandardDeviation(values: number[]): number {
  if (values.length === 0) return 0;
  
  const mean = calculateMean(values);
  const squaredDifferences = values.map(value => Math.pow(value - mean, 2));
  const variance = calculateMean(squaredDifferences);
  
  return Math.sqrt(variance);
}

export function calculateCoefficientOfVariation(values: number[]): number {
  const mean = calculateMean(values);
  if (mean === 0) return 0;
  
  const stdDev = calculateStandardDeviation(values);
  return (stdDev / mean) * 100;
}

// Property ratios and metrics
export function calculatePricePerSquareFoot(price: number, squareFootage: number): number {
  if (squareFootage === 0) return 0;
  return price / squareFootage;
}

export function calculateLandToTotalRatio(landValue: number, totalValue: number): number {
  if (totalValue === 0) return 0;
  return (landValue / totalValue) * 100;
}

export function calculateImprovementToLandRatio(
  improvementValue: number,
  landValue: number
): number {
  if (landValue === 0) return 0;
  return (improvementValue / landValue) * 100;
}

export function calculateBuildingResidualValue(
  totalValue: number,
  landValue: number,
  entrepreneurialIncentive: number = 0
): number {
  return Math.max(0, totalValue - landValue - entrepreneurialIncentive);
}

// Assessment quality metrics
export function calculateAssessmentRatio(assessedValue: number, marketValue: number): number {
  if (marketValue === 0) return 0;
  return (assessedValue / marketValue) * 100;
}

export function calculateCoefficientOfDispersion(assessmentRatios: number[]): number {
  if (assessmentRatios.length === 0) return 0;
  
  const median = calculateMedian(assessmentRatios);
  if (median === 0) return 0;
  
  const absoluteDeviations = assessmentRatios.map(ratio => Math.abs(ratio - median));
  const meanAbsoluteDeviation = calculateMean(absoluteDeviations);
  
  return (meanAbsoluteDeviation / median) * 100;
}

export function calculatePriceRelatedDifferential(
  assessmentRatios: number[],
  marketValues: number[]
): number {
  if (assessmentRatios.length !== marketValues.length || assessmentRatios.length === 0) {
    return 0;
  }
  
  // Calculate weighted mean assessment ratio
  const totalValue = marketValues.reduce((sum, value) => sum + value, 0);
  const weightedSum = assessmentRatios.reduce((sum, ratio, index) => 
    sum + (ratio * marketValues[index]), 0
  );
  const weightedMean = weightedSum / totalValue;
  
  // Calculate mean assessment ratio
  const mean = calculateMean(assessmentRatios);
  
  if (mean === 0) return 0;
  return ((weightedMean - mean) / mean) * 100;
}

// Utility functions for assessment calculations
export function interpolateValue(
  x: number,
  x1: number,
  y1: number,
  x2: number,
  y2: number
): number {
  if (x2 === x1) return y1;
  return y1 + ((x - x1) * (y2 - y1)) / (x2 - x1);
}

export function extrapolateValue(
  x: number,
  x1: number,
  y1: number,
  x2: number,
  y2: number
): number {
  return interpolateValue(x, x1, y1, x2, y2);
}

export function calculateWeightedAverage(
  values: number[],
  weights: number[]
): number {
  if (values.length !== weights.length || values.length === 0) {
    return 0;
  }
  
  const totalWeight = weights.reduce((sum, weight) => sum + weight, 0);
  if (totalWeight === 0) return 0;
  
  const weightedSum = values.reduce((sum, value, index) => 
    sum + (value * weights[index]), 0
  );
  
  return weightedSum / totalWeight;
}