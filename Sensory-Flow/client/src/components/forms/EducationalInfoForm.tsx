import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { BookOpen, GraduationCap, School } from "lucide-react";

import { educationalInfoSchema, type EducationalInfoData, yesNoOptions, educationTypeOptions } from "@shared/schema";
import { useAssessment } from "@/context/AssessmentContext";

import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormSection } from "@/components/FormSection";
import { FormNavigation } from "@/components/FormNavigation";
import { RequiredLabel } from "@/components/RequiredLabel";
import { cn } from "@/lib/utils";

export function EducationalInfoForm() {
  const { educationalInfo, setEducationalInfo, setCurrentStep } = useAssessment();

  const form = useForm<EducationalInfoData>({
    resolver: zodResolver(educationalInfoSchema),
    defaultValues: {
      enrolledInSchool: educationalInfo.enrolledInSchool,
      educationType: educationalInfo.educationType,
      standardClass: educationalInfo.standardClass || "",
      schoolName: educationalInfo.schoolName || ""
    }
  });

  const enrolledInSchool = form.watch("enrolledInSchool");

  const onSubmit = (data: EducationalInfoData) => {
    setEducationalInfo(data);
    setCurrentStep(4);
  };

  const handleBack = () => {
    setEducationalInfo(form.getValues());
    setCurrentStep(2);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormSection
          title="Educational Information"
          description="Details about the child's educational background"
          icon={<BookOpen className="w-5 h-5" />}
        >
          <div className="space-y-6">
            <FormField
              control={form.control}
              name="enrolledInSchool"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Enrolled in School</RequiredLabel>
                  </FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger data-testid="select-enrolled-in-school">
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

            <div
              className={cn(
                "space-y-6 p-6 bg-muted/30 rounded-lg border border-border transition-all duration-200",
                enrolledInSchool === "Yes" ? "opacity-100" : "opacity-0 h-0 p-0 overflow-hidden border-0"
              )}
            >
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <FormField
                  control={form.control}
                  name="educationType"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        <RequiredLabel required>Type of Education</RequiredLabel>
                      </FormLabel>
                      <Select onValueChange={field.onChange} defaultValue={field.value}>
                        <FormControl>
                          <SelectTrigger data-testid="select-education-type">
                            <SelectValue placeholder="Select education type" />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {educationTypeOptions.map((option) => (
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

                <FormField
                  control={form.control}
                  name="standardClass"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>
                        <RequiredLabel required>Standard / Class</RequiredLabel>
                      </FormLabel>
                      <FormControl>
                        <div className="relative">
                          <GraduationCap className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                          <Input 
                            className="pl-10" 
                            placeholder="e.g., 1st Grade, LKG"
                            {...field} 
                            data-testid="input-standard-class"
                          />
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                <FormField
                  control={form.control}
                  name="schoolName"
                  render={({ field }) => (
                    <FormItem className="md:col-span-2">
                      <FormLabel>
                        <RequiredLabel optional>Name of the School</RequiredLabel>
                      </FormLabel>
                      <FormControl>
                        <div className="relative">
                          <School className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                          <Input 
                            className="pl-10" 
                            placeholder="Enter school name"
                            {...field} 
                            data-testid="input-school-name"
                          />
                        </div>
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
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
