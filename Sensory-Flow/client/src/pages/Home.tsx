import { Link } from "wouter";
import { 
  Activity, 
  ClipboardCheck, 
  FileText, 
  ArrowRight, 
  Shield,
  Brain,
  Users,
  Zap
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

export default function Home() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-primary text-primary-foreground">
              <Activity className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">SensoryAssess Pro</h1>
              <p className="text-xs text-muted-foreground">AI-Assisted Assessment System</p>
            </div>
          </div>
          <Link href="/assessment">
            <Button data-testid="button-start-assessment">
              Start Assessment
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </Link>
        </div>
      </header>

      <main>
        <section className="py-20 px-4">
          <div className="max-w-4xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
              <Brain className="w-4 h-4" />
              <span>Vestibular Proprioceptive Processing Assessment</span>
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-foreground mb-6 leading-tight">
              AI-Powered Sensory Integration Assessment for Children
            </h2>
            <p className="text-lg text-muted-foreground mb-8 max-w-2xl mx-auto">
              A comprehensive, clinically validated assessment tool designed for healthcare 
              professionals to evaluate sensory processing in children aged 6-7 years 
              using advanced computer vision technology.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Link href="/assessment">
                <Button size="lg" data-testid="button-hero-start">
                  <ClipboardCheck className="w-5 h-5 mr-2" />
                  Begin New Assessment
                </Button>
              </Link>
              <Button size="lg" variant="outline" data-testid="button-learn-more">
                Learn More
              </Button>
            </div>
          </div>
        </section>

        <section className="py-16 px-4 bg-muted/30">
          <div className="max-w-6xl mx-auto">
            <h3 className="text-2xl font-semibold text-foreground text-center mb-12">
              Assessment Features
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center text-center">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                      <Brain className="w-6 h-6 text-primary" />
                    </div>
                    <h4 className="font-semibold text-foreground mb-2">AI Analysis</h4>
                    <p className="text-sm text-muted-foreground">
                      Advanced computer vision models analyze movement patterns with clinical precision
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center text-center">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                      <Activity className="w-6 h-6 text-primary" />
                    </div>
                    <h4 className="font-semibold text-foreground mb-2">9 Exercise Tests</h4>
                    <p className="text-sm text-muted-foreground">
                      Comprehensive assessment including prone extension, balance, and coordination tests
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center text-center">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                      <FileText className="w-6 h-6 text-primary" />
                    </div>
                    <h4 className="font-semibold text-foreground mb-2">Detailed Reports</h4>
                    <p className="text-sm text-muted-foreground">
                      Generate comprehensive PDF reports with scores and clinical observations
                    </p>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6">
                  <div className="flex flex-col items-center text-center">
                    <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                      <Shield className="w-6 h-6 text-primary" />
                    </div>
                    <h4 className="font-semibold text-foreground mb-2">Clinical Grade</h4>
                    <p className="text-sm text-muted-foreground">
                      Validated scoring system aligned with established clinical standards
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </section>

        <section className="py-16 px-4">
          <div className="max-w-6xl mx-auto">
            <h3 className="text-2xl font-semibold text-foreground text-center mb-12">
              Exercise Assessments
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { name: "Prone Extension", description: "Tests anti-gravity extension in prone position" },
                { name: "Supine Flexion", description: "Evaluates flexor muscle coordination" },
                { name: "One Leg Standing", description: "Assesses balance with eyes open/closed" },
                { name: "Tandem Walking", description: "Heel-to-toe walking coordination" },
                { name: "Jumping Jacks", description: "Bilateral motor coordination assessment" },
                { name: "Balance Tests", description: "Left/right leg lift variations" }
              ].map((exercise, index) => (
                <div 
                  key={index}
                  className="flex items-start gap-3 p-4 rounded-lg border border-border bg-card"
                >
                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary text-sm font-semibold flex-shrink-0">
                    {index + 1}
                  </div>
                  <div>
                    <h4 className="font-medium text-foreground">{exercise.name}</h4>
                    <p className="text-sm text-muted-foreground">{exercise.description}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="py-16 px-4 bg-primary text-primary-foreground">
          <div className="max-w-4xl mx-auto text-center">
            <h3 className="text-2xl font-semibold mb-4">
              Ready to Start an Assessment?
            </h3>
            <p className="text-primary-foreground/80 mb-8">
              Complete the registration form and begin evaluating sensory processing capabilities.
            </p>
            <Link href="/assessment">
              <Button size="lg" variant="secondary" data-testid="button-cta-start">
                <ClipboardCheck className="w-5 h-5 mr-2" />
                Start New Assessment
              </Button>
            </Link>
          </div>
        </section>

        <section className="py-16 px-4">
          <div className="max-w-6xl mx-auto">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
              <div>
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mx-auto mb-4">
                  <Users className="w-6 h-6 text-primary" />
                </div>
                <h4 className="font-semibold text-foreground mb-2">Target Population</h4>
                <p className="text-sm text-muted-foreground">
                  Typically developing children and children with sensory processing disorders aged 6-7 years
                </p>
              </div>
              <div>
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mx-auto mb-4">
                  <Zap className="w-6 h-6 text-primary" />
                </div>
                <h4 className="font-semibold text-foreground mb-2">Fast Results</h4>
                <p className="text-sm text-muted-foreground">
                  AI-powered analysis delivers results in minutes, not hours
                </p>
              </div>
              <div>
                <div className="flex items-center justify-center w-12 h-12 rounded-full bg-primary/10 mx-auto mb-4">
                  <Shield className="w-6 h-6 text-primary" />
                </div>
                <h4 className="font-semibold text-foreground mb-2">Secure & Private</h4>
                <p className="text-sm text-muted-foreground">
                  All assessment data is handled with strict healthcare privacy standards
                </p>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border py-8 px-4 bg-card">
        <div className="max-w-6xl mx-auto text-center">
          <div className="flex items-center justify-center gap-2 mb-4">
            <Activity className="w-5 h-5 text-primary" />
            <span className="font-semibold text-foreground">SensoryAssess Pro</span>
          </div>
          <p className="text-sm text-muted-foreground">
            AI-Assisted Sensory Integration Assessment System for Healthcare Professionals
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            Vestibular Proprioceptive Processing Assessment (Bundy & Lane, 2020)
          </p>
        </div>
      </footer>
    </div>
  );
}
