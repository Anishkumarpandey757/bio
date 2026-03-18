import type { ReactNode } from "react";

interface RequiredLabelProps {
  children: ReactNode;
  required?: boolean;
  optional?: boolean;
}

export function RequiredLabel({ children, required = false, optional = false }: RequiredLabelProps) {
  return (
    <span className="flex items-center gap-1">
      {children}
      {required && <span className="text-destructive">*</span>}
      {optional && <span className="text-muted-foreground text-xs font-normal">(Optional)</span>}
    </span>
  );
}
