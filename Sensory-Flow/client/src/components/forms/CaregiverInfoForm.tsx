import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Users, User, Phone, Heart } from "lucide-react";

import { caregiverInfoSchema, type CaregiverInfoData } from "@shared/schema";
import { useAssessment } from "@/context/AssessmentContext";

import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { FormSection } from "@/components/FormSection";
import { FormNavigation } from "@/components/FormNavigation";
import { RequiredLabel } from "@/components/RequiredLabel";

export function CaregiverInfoForm() {
  const { caregiverInfo, setCaregiverInfo, setCurrentStep } = useAssessment();

  const form = useForm<CaregiverInfoData>({
    resolver: zodResolver(caregiverInfoSchema),
    defaultValues: {
      caregiverName: caregiverInfo.caregiverName || "",
      relationToChild: caregiverInfo.relationToChild || "",
      caregiverContact: caregiverInfo.caregiverContact || ""
    }
  });

  const onSubmit = (data: CaregiverInfoData) => {
    setCaregiverInfo(data);
    setCurrentStep(5);
  };

  const handleBack = () => {
    setCaregiverInfo(form.getValues());
    setCurrentStep(3);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormSection
          title="Caregiver Information"
          description="Contact details of the child's primary caregiver (all fields optional)"
          icon={<Users className="w-5 h-5" />}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              control={form.control}
              name="caregiverName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel optional>Caregiver's Name</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        className="pl-10" 
                        placeholder="Enter caregiver's name"
                        {...field} 
                        data-testid="input-caregiver-name"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="relationToChild"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel optional>Relation to Child</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Heart className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        className="pl-10" 
                        placeholder="e.g., Mother, Father, Guardian"
                        {...field} 
                        data-testid="input-relation-to-child"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="caregiverContact"
              render={({ field }) => (
                <FormItem className="md:col-span-2">
                  <FormLabel>
                    <RequiredLabel optional>Caregiver's Contact Number</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Phone className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        className="pl-10" 
                        placeholder="+91 XXXXX XXXXX"
                        {...field} 
                        data-testid="input-caregiver-contact"
                      />
                    </div>
                  </FormControl>
                  <p className="text-sm text-muted-foreground mt-1">
                    Include country code if applicable
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
