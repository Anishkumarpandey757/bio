import { ArrowLeft, ArrowRight, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FormNavigationProps {
  onBack?: () => void;
  onNext?: () => void;
  isFirstStep?: boolean;
  isLastStep?: boolean;
  isSubmitting?: boolean;
  nextLabel?: string;
  backLabel?: string;
  nextDisabled?: boolean;
}

export function FormNavigation({
  onBack,
  onNext,
  isFirstStep = false,
  isLastStep = false,
  isSubmitting = false,
  nextLabel = "Next Step",
  backLabel = "Back",
  nextDisabled = false
}: FormNavigationProps) {
  return (
    <div className="flex items-center justify-between gap-4 pt-6 border-t border-border mt-8">
      <div>
        {!isFirstStep && onBack && (
          <Button
            type="button"
            variant="outline"
            onClick={onBack}
            disabled={isSubmitting}
            data-testid="button-back"
          >
            <ArrowLeft className="w-4 h-4 mr-2" />
            {backLabel}
          </Button>
        )}
      </div>
      <div>
        {onNext && (
          <Button
            type={isLastStep ? "submit" : "button"}
            onClick={isLastStep ? undefined : onNext}
            disabled={isSubmitting || nextDisabled}
            data-testid="button-next"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Processing...
              </>
            ) : (
              <>
                {nextLabel}
                {!isLastStep && <ArrowRight className="w-4 h-4 ml-2" />}
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}
