import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Heart, Info } from "lucide-react";

import { birthMedicalSchema, type BirthMedicalData, yesNoOptions } from "@shared/schema";
import { useAssessment } from "@/context/AssessmentContext";

import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormSection } from "@/components/FormSection";
import { FormNavigation } from "@/components/FormNavigation";
import { RequiredLabel } from "@/components/RequiredLabel";
import { cn } from "@/lib/utils";

interface ConditionalFieldProps {
  show: boolean;
  children: React.ReactNode;
}

function ConditionalField({ show, children }: ConditionalFieldProps) {
  return (
    <div
      className={cn(
        "ml-4 mt-3 p-4 bg-muted/50 rounded-lg border border-border transition-all duration-200",
        show ? "opacity-100" : "opacity-0 h-0 p-0 m-0 overflow-hidden border-0"
      )}
    >
      {children}
    </div>
  );
}

export function BirthMedicalForm() {
  const { birthMedical, setBirthMedical, setCurrentStep } = useAssessment();

  const form = useForm<BirthMedicalData>({
    resolver: zodResolver(birthMedicalSchema),
    defaultValues: {
      lowBirthWeight: birthMedical.lowBirthWeight,
      lowBirthWeightDetails: birthMedical.lowBirthWeightDetails || "",
      premature: birthMedical.premature,
      prematureDetails: birthMedical.prematureDetails || "",
      birthComplications: birthMedical.birthComplications,
      birthComplicationsDetails: birthMedical.birthComplicationsDetails || "",
      developmentalDisability: birthMedical.developmentalDisability,
      developmentalDisabilityDetails: birthMedical.developmentalDisabilityDetails || ""
    }
  });

  const lowBirthWeight = form.watch("lowBirthWeight");
  const premature = form.watch("premature");
  const birthComplications = form.watch("birthComplications");
  const developmentalDisability = form.watch("developmentalDisability");

  const onSubmit = (data: BirthMedicalData) => {
    setBirthMedical(data);
    setCurrentStep(2);
  };

  const handleBack = () => {
    setBirthMedical(form.getValues());
    setCurrentStep(0);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormSection
          title="Birth and Medical History"
          description="Document the child's birth and medical background"
          icon={<Heart className="w-5 h-5" />}
        >
          <div className="space-y-6">
            <div>
              <FormField
                control={form.control}
                name="lowBirthWeight"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      <RequiredLabel required>Low Birth Weight</RequiredLabel>
                    </FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger data-testid="select-low-birth-weight">
                          <SelectValue placeholder="Select Yes or No" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {yesNoOptions.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <ConditionalField show={lowBirthWeight === "Yes"}>
                <FormField
                  control={form.control}
                  name="lowBirthWeightDetails"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="flex items-center gap-2">
                        <Info className="w-4 h-4" />
                        Specify weight
                      </FormLabel>
                      <FormControl>
                        <Input 
                          placeholder="e.g., 2.1 kg" 
                          {...field} 
                          data-testid="input-low-birth-weight-details"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </ConditionalField>
            </div>

            <div>
              <FormField
                control={form.control}
                name="premature"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      <RequiredLabel required>Premature Birth</RequiredLabel>
                    </FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger data-testid="select-premature">
                          <SelectValue placeholder="Select Yes or No" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {yesNoOptions.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <ConditionalField show={premature === "Yes"}>
                <FormField
                  control={form.control}
                  name="prematureDetails"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="flex items-center gap-2">
                        <Info className="w-4 h-4" />
                        Specify gestational age
                      </FormLabel>
                      <FormControl>
                        <Input 
                          placeholder="e.g., 34 weeks" 
                          {...field} 
                          data-testid="input-premature-details"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </ConditionalField>
            </div>

            <div>
              <FormField
                control={form.control}
                name="birthComplications"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      <RequiredLabel required>Birth Complications</RequiredLabel>
                    </FormLabel>
                    <p className="text-sm text-muted-foreground mb-2">
                      e.g., hypoxia, jaundice, NICU stay
                    </p>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger data-testid="select-birth-complications">
                          <SelectValue placeholder="Select Yes or No" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {yesNoOptions.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <ConditionalField show={birthComplications === "Yes"}>
                <FormField
                  control={form.control}
                  name="birthComplicationsDetails"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="flex items-center gap-2">
                        <Info className="w-4 h-4" />
                        Specify complications
                      </FormLabel>
                      <FormControl>
                        <Input 
                          placeholder="Describe the complications" 
                          {...field} 
                          data-testid="input-birth-complications-details"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </ConditionalField>
            </div>

            <div>
              <FormField
                control={form.control}
                name="developmentalDisability"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>
                      <RequiredLabel required>Any Developmental Disability / Medical Condition</RequiredLabel>
                    </FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger data-testid="select-developmental-disability">
                          <SelectValue placeholder="Select Yes or No" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        {yesNoOptions.map((option) => (
                          <SelectItem key={option} value={option}>
                            {option}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />
              <ConditionalField show={developmentalDisability === "Yes"}>
                <FormField
                  control={form.control}
                  name="developmentalDisabilityDetails"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel className="flex items-center gap-2">
                        <Info className="w-4 h-4" />
                        Specify diagnosis
                      </FormLabel>
                      <FormControl>
                        <Input 
                          placeholder="Enter diagnosis details" 
                          {...field} 
                          data-testid="input-developmental-disability-details"
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </ConditionalField>
            </div>
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
