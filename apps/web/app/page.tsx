import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { MapPin, Home, TrendingUp, Users } from 'lucide-react';

export default function HomePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      {/* Hero Section */}
      <section className="text-center py-20">
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6">
          Property Assessment
          <span className="text-primary"> Platform</span>
        </h1>
        <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
          Modern, efficient, and accurate property assessment solutions powered by advanced technology and expert insights.
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Button size="lg" className="text-lg px-8">
            Get Started
          </Button>
          <Button variant="outline" size="lg" className="text-lg px-8">
            Learn More
          </Button>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-20">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold mb-4">Why Choose Our Platform?</h2>
          <p className="text-muted-foreground text-lg max-w-2xl mx-auto">
            Experience the future of property assessment with our comprehensive suite of tools and services.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card className="text-center">
            <CardHeader>
              <MapPin className="h-12 w-12 mx-auto text-primary mb-4" />
              <CardTitle>Location Intelligence</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Advanced mapping and location-based analytics for accurate property evaluation.
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="text-center">
            <CardHeader>
              <Home className="h-12 w-12 mx-auto text-primary mb-4" />
              <CardTitle>Property Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Comprehensive property data analysis and valuation tools for informed decisions.
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="text-center">
            <CardHeader>
              <TrendingUp className="h-12 w-12 mx-auto text-primary mb-4" />
              <CardTitle>Market Insights</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Real-time market trends and predictive analytics for strategic planning.
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="text-center">
            <CardHeader>
              <Users className="h-12 w-12 mx-auto text-primary mb-4" />
              <CardTitle>Expert Support</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
                Professional guidance from certified property assessment experts.
              </CardDescription>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 text-center">
        <Card className="max-w-4xl mx-auto">
          <CardHeader className="pb-8">
            <CardTitle className="text-3xl">Ready to Get Started?</CardTitle>
            <CardDescription className="text-lg">
              Join thousands of professionals who trust our platform for accurate property assessments.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" className="text-lg px-8">
                Start Free Trial
              </Button>
              <Button variant="outline" size="lg" className="text-lg px-8">
                Contact Sales
              </Button>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}