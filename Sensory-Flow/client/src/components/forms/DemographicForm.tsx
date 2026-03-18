import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { User, CalendarDays, Calculator } from "lucide-react";
import { useEffect } from "react";
import { differenceInYears, differenceInMonths, parse, isValid } from "date-fns";

import { demographicSchema, type DemographicData, genderOptions } from "@shared/schema";
import { useAssessment } from "@/context/AssessmentContext";

import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { FormSection } from "@/components/FormSection";
import { FormNavigation } from "@/components/FormNavigation";
import { RequiredLabel } from "@/components/RequiredLabel";

export function DemographicForm() {
  const { demographic, setDemographic, setCurrentStep } = useAssessment();

  const form = useForm<DemographicData>({
    resolver: zodResolver(demographicSchema),
    defaultValues: {
      childName: demographic.childName || "",
      gender: demographic.gender,
      dateOfBirth: demographic.dateOfBirth || "",
      dateOfAssessment: demographic.dateOfAssessment || new Date().toISOString().split("T")[0],
      calculatedAge: demographic.calculatedAge || ""
    }
  });

  const dateOfBirth = form.watch("dateOfBirth");
  const dateOfAssessment = form.watch("dateOfAssessment");

  useEffect(() => {
    if (dateOfBirth && dateOfAssessment) {
      const dob = parse(dateOfBirth, "yyyy-MM-dd", new Date());
      const assessmentDate = parse(dateOfAssessment, "yyyy-MM-dd", new Date());

      if (isValid(dob) && isValid(assessmentDate) && assessmentDate > dob) {
        const years = differenceInYears(assessmentDate, dob);
        const totalMonths = differenceInMonths(assessmentDate, dob);
        const months = totalMonths % 12;
        const ageString = `${years} years, ${months} months`;
        form.setValue("calculatedAge", ageString);
      } else {
        form.setValue("calculatedAge", "");
      }
    }
  }, [dateOfBirth, dateOfAssessment, form]);

  const onSubmit = (data: DemographicData) => {
    setDemographic(data);
    setCurrentStep(1);
  };

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
        <FormSection
          title="Demographic Details"
          description="Enter the child's basic information for assessment records"
          icon={<User className="w-5 h-5" />}
        >
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              control={form.control}
              name="childName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Child's Name</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <Input 
                      placeholder="Enter child's full name" 
                      {...field} 
                      data-testid="input-child-name"
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="gender"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Gender</RequiredLabel>
                  </FormLabel>
                  <Select onValueChange={field.onChange} defaultValue={field.value}>
                    <FormControl>
                      <SelectTrigger data-testid="select-gender">
                        <SelectValue placeholder="Select gender" />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      {genderOptions.map((option) => (
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
              name="dateOfBirth"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Date of Birth</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <CalendarDays className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        type="date" 
                        className="pl-10" 
                        {...field} 
                        data-testid="input-date-of-birth"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="dateOfAssessment"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>
                    <RequiredLabel required>Date of Assessment</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <CalendarDays className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        type="date" 
                        className="pl-10" 
                        {...field} 
                        data-testid="input-date-of-assessment"
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="calculatedAge"
              render={({ field }) => (
                <FormItem className="md:col-span-2">
                  <FormLabel>
                    <RequiredLabel required>Age (Auto-calculated)</RequiredLabel>
                  </FormLabel>
                  <FormControl>
                    <div className="relative">
                      <Calculator className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                      <Input 
                        className="pl-10 bg-primary/5 font-medium" 
                        readOnly 
                        placeholder="Will be calculated from DOB and assessment date"
                        {...field} 
                        data-testid="input-calculated-age"
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
          isFirstStep={true}
          onNext={form.handleSubmit(onSubmit)}
        />
      </form>
    </Form>
  );
}
