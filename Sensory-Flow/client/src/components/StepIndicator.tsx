import { Check, User, Heart, Scale, BookOpen, Users, Stethoscope, Calendar, Activity, FileText } from "lucide-react";
import { cn } from "@/lib/utils";

interface Step {
  id: number;
  name: string;
  shortName: string;
  icon: typeof User;
}

const steps: Step[] = [
  { id: 0, name: "Demographics", shortName: "Demographics", icon: User },
  { id: 1, name: "Medical History", shortName: "Medical", icon: Heart },
  { id: 2, name: "Physical Parameters", shortName: "Physical", icon: Scale },
  { id: 3, name: "Education", shortName: "Education", icon: BookOpen },
  { id: 4, name: "Caregiver", shortName: "Caregiver", icon: Users },
  { id: 5, name: "Therapist Details", shortName: "Therapist", icon: Stethoscope },
  { id: 6, name: "Age Selection", shortName: "Age", icon: Calendar },
  { id: 7, name: "Exercise Upload", shortName: "Exercises", icon: Activity },
  { id: 8, name: "Results & Report", shortName: "Report", icon: FileText }
];

interface StepIndicatorProps {
  currentStep: number;
  className?: string;
}

export function StepIndicator({ currentStep, className }: StepIndicatorProps) {
  return (
    <div className={cn("w-full py-4", className)}>
      <div className="flex items-center justify-between max-w-5xl mx-auto px-4">
        {steps.map((step, index) => {
          const isCompleted = currentStep > step.id;
          const isCurrent = currentStep === step.id;
          const Icon = step.icon;

          return (
            <div key={step.id} className="flex items-center flex-1 last:flex-none">
              <div className="flex flex-col items-center">
                <div
                  className={cn(
                    "flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-200",
                    isCompleted && "bg-primary border-primary text-primary-foreground",
                    isCurrent && "border-primary bg-primary/10 text-primary",
                    !isCompleted && !isCurrent && "border-muted-foreground/30 text-muted-foreground/50"
                  )}
                  data-testid={`step-indicator-${step.id}`}
                >
                  {isCompleted ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    <Icon className="w-5 h-5" />
                  )}
                </div>
                <span
                  className={cn(
                    "mt-2 text-xs font-medium text-center hidden md:block",
                    isCurrent && "text-primary font-semibold",
                    isCompleted && "text-primary",
                    !isCompleted && !isCurrent && "text-muted-foreground"
                  )}
                >
                  {step.shortName}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-0.5 mx-2 transition-all duration-200",
                    isCompleted ? "bg-primary" : "bg-muted-foreground/20"
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
      <div className="text-center mt-4 md:hidden">
        <span className="text-sm font-medium text-foreground">
          Step {currentStep + 1} of {steps.length}: {steps[currentStep]?.name}
        </span>
      </div>
    </div>
  );
}
