import { useState } from "react";
import { Calendar, AlertCircle, CheckCircle2 } from "lucide-react";

import { ageGroupOptions } from "@shared/schema";
import { useAssessment } from "@/context/AssessmentContext";

import { FormSection } from "@/components/FormSection";
import { FormNavigation } from "@/components/FormNavigation";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function AgeGroupSelection() {
  const { ageGroup, setAgeGroup, setCurrentStep, demographic } = useAssessment();
  const [selectedAge, setSelectedAge] = useState(ageGroup);

  const handleSelect = (option: string) => {
    setSelectedAge(option);
  };

  const handleNext = () => {
    if (selectedAge) {
      setAgeGroup(selectedAge);
      setCurrentStep(7);
    }
  };

  const handleBack = () => {
    setCurrentStep(5);
  };

  const getAgeGroupIcon = (option: string) => {
    if (option === "6 years 0 months – 6 years 11 months") {
      return "6";
    } else if (option === "7 years 0 months – 7 years 11 months") {
      return "7";
    }
    return "?";
  };

  const isStandardAgeGroup = (option: string) => {
    return option !== "Other age groups";
  };

  return (
    <div className="space-y-8">
      <FormSection
        title="Age Group Selection"
        description="Select the appropriate age group for assessment scoring. The standard assessment is designed for children aged 6-7 years."
        icon={<Calendar className="w-5 h-5" />}
      >
        {demographic.calculatedAge && (
          <div className="flex items-center gap-3 p-4 bg-primary/10 rounded-lg border border-primary/20 mb-6">
            <CheckCircle2 className="w-5 h-5 text-primary flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-foreground">Child's Current Age</p>
              <p className="text-lg font-semibold text-primary">{demographic.calculatedAge}</p>
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {ageGroupOptions.map((option) => {
            const isSelected = selectedAge === option;
            const isStandard = isStandardAgeGroup(option);

            return (
              <Card
                key={option}
                className={cn(
                  "relative p-6 cursor-pointer transition-all duration-200 hover-elevate",
                  isSelected && "ring-2 ring-primary bg-primary/5",
                  !isSelected && "hover:border-primary/50"
                )}
                onClick={() => handleSelect(option)}
                data-testid={`card-age-group-${option.replace(/\s+/g, "-").toLowerCase()}`}
              >
                <div className="flex flex-col items-center text-center space-y-3">
                  <div
                    className={cn(
                      "flex items-center justify-center w-16 h-16 rounded-full text-2xl font-bold",
                      isSelected
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground"
                    )}
                  >
                    {isStandard ? getAgeGroupIcon(option) : (
                      <AlertCircle className="w-8 h-8" />
                    )}
                  </div>
                  <div>
                    <p className="font-semibold text-foreground">{option}</p>
                    {isStandard ? (
                      <p className="text-xs text-muted-foreground mt-1">
                        Full scoring available (0-3 scale)
                      </p>
                    ) : (
                      <p className="text-xs text-muted-foreground mt-1">
                        Values only (no scoring)
                      </p>
                    )}
                  </div>
                </div>
                {isSelected && (
                  <div className="absolute top-3 right-3">
                    <CheckCircle2 className="w-5 h-5 text-primary" />
                  </div>
                )}
              </Card>
            );
          })}
        </div>

        <div className="mt-6 p-4 bg-muted/50 rounded-lg border border-border">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-muted-foreground flex-shrink-0 mt-0.5" />
            <div className="text-sm text-muted-foreground">
              <p className="font-medium text-foreground mb-1">Important Note</p>
              <p>
                If the child's age falls between 6 years 0 months to 7 years 11 months, 
                the report will include both values (angles, cm, seconds) and scores (0,1,2,3). 
                For other age groups, only values will be displayed in the report.
              </p>
            </div>
          </div>
        </div>
      </FormSection>

      <FormNavigation
        onBack={handleBack}
        onNext={handleNext}
        nextLabel="Continue to Exercises"
        nextDisabled={!selectedAge}
      />
    </div>
  );
}
