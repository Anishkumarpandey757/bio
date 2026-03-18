import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Scale, Ruler, Calculator } from "lucide-react";
import { useEffect } from "react";

import { physicalParametersSchema, type PhysicalParametersData } from "@shared/schema";
import { useAssessment } from "@/context/AssessmentContext";

import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { FormSection } from "@/components/FormSection";
import { FormNavigation } from "@/components/FormNavigation";
import { RequiredLabel } from "@/components/RequiredLabel";

export function PhysicalParametersForm() {
  const { physicalParameters, setPhysicalParameters, setCurrentStep } = useAssessment();

  const form = useForm<PhysicalParametersData>({
    resolver: zodResolver(physicalParametersSchema),
    defaultValues: {
      height: physicalParameters.height || undefined,
      weight: physicalParameters.weight || undefined,
      bmi: physicalParameters.bmi || undefined
    }
  });

  const height = form.watch("height");
  const weight = form.watch("weight");

  useEffect(() => {
    if (height && weight && height > 0) {
      const bmiValue = weight / (height * height);
      form.setValue("bmi", Math.round(bmiValue * 10) / 10);
    }
  }, [height, weight, form]);

  const onSubmit = (data: PhysicalParametersData) => {
    setPhysicalParameters(data);
    setCurrentStep(3);
  };

  const handleBack = () => {
    const values = form.getValues();
    setPhysicalParameters({
      height: values.height,
      weight: values.weight,
      bmi: values.bmi
    });
    setCurrentStep(1);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormSection
          title="Physical Parameters"
          description="Record the child's current physical measurements"
          icon={<Scale className="w-5 h-5" />}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              control={form.control}
              name="height"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Height (meters)</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Ruler className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        type="number"
                        step="0.01"
                        min="0.1"
                        max="2.5"
                        className="pl-10" 
                        placeholder="e.g., 1.15"
                        {...field}
                        onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : undefined)}
                        value={field.value ?? ""}
                        data-testid="input-height"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="weight"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Weight (kg)</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Scale className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        type="number"
                        step="0.1"
                        min="1"
                        max="200"
                        className="pl-10" 
                        placeholder="e.g., 20.5"
                        {...field}
                        onChange={(e) => field.onChange(e.target.value ? parseFloat(e.target.value) : undefined)}
                        value={field.value ?? ""}
                        data-testid="input-weight"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="bmi"
              render={({ field }) => (
                <FormItem className="md:col-span-2">
                  <FormLabel>
                    <RequiredLabel required>BMI (Auto-calculated)</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Calculator className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        className="pl-10 bg-primary/5 font-mono font-medium" 
                        readOnly 
                        placeholder="Will be calculated from height and weight"
                        value={field.value ? `${field.value} kg/m²` : ""}
                        data-testid="input-bmi"
                      />
                    </div>
                  </FormControl>
                  <p className="text-sm text-muted-foreground mt-1">
                    BMI = Weight (kg) / Height² (m²)
                  </p>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </FormSection>

        <FormNavigation 
          onBack={handleBack}
          onNext={form.handleSubmit(onSubmit)}
        />
      </form>
    </Form>
  );
}
