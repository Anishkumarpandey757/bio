import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Stethoscope, User, Briefcase, BadgeCheck, Building2 } from "lucide-react";

import { therapistInfoSchema, type TherapistInfoData } from "@shared/schema";
import { useAssessment } from "@/context/AssessmentContext";

import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FormSection } from "@/components/FormSection";
import { FormNavigation } from "@/components/FormNavigation";
import { RequiredLabel } from "@/components/RequiredLabel";

export function TherapistInfoForm() {
  const { therapistInfo, setTherapistInfo, setCurrentStep } = useAssessment();

  const form = useForm<TherapistInfoData>({
    resolver: zodResolver(therapistInfoSchema),
    defaultValues: {
      therapistName: therapistInfo.therapistName || "",
      therapistProfession: therapistInfo.therapistProfession || "",
      licenseNumber: therapistInfo.licenseNumber || "",
      therapistDesignation: therapistInfo.therapistDesignation || "",
      serviceProviderDetails: therapistInfo.serviceProviderDetails || ""
    }
  });

  const onSubmit = (data: TherapistInfoData) => {
    setTherapistInfo(data);
    setCurrentStep(6);
  };

  const handleBack = () => {
    setTherapistInfo(form.getValues());
    setCurrentStep(4);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormSection
          title="Therapist / Examiner Details"
          description="Information about the healthcare professional conducting the assessment"
          icon={<Stethoscope className="w-5 h-5" />}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              control={form.control}
              name="therapistName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Therapist / Examiner Name</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        className="pl-10" 
                        placeholder="Enter full name"
                        {...field} 
                        data-testid="input-therapist-name"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="therapistProfession"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Profession</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        className="pl-10" 
                        placeholder="e.g., Physiotherapist, Occupational Therapist"
                        {...field} 
                        data-testid="input-therapist-profession"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="licenseNumber"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel optional>Professional License Number</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <BadgeCheck className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        className="pl-10" 
                        placeholder="Enter license number"
                        {...field} 
                        data-testid="input-license-number"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="therapistDesignation"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Designation</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Briefcase className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        className="pl-10" 
                        placeholder="e.g., Senior Physiotherapist, Clinical Lead"
                        {...field} 
                        data-testid="input-therapist-designation"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="serviceProviderDetails"
              render={({ field }) => (
                <FormItem className="md:col-span-2">
                  <FormLabel>
                    <RequiredLabel required>Service Provider / Hospital / Rehab Centre</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Building2 className="absolute left-3 top-3 w-4 h-4 text-muted-foreground" />
                      <Textarea 
                        className="pl-10 min-h-[100px] resize-none" 
                        placeholder="Enter name and full address of the service provider"
                        {...field} 
                        data-testid="input-service-provider-details"
                      />
                    </div>
                  </FormControl>
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
