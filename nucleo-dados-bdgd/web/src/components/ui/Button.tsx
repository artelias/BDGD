import { forwardRef, type ButtonHTMLAttributes } from "react";
import s from "./ui.module.css";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "default" | "primary" | "ghost"; size?: "md" | "sm"; icon?: boolean };

export const Button = forwardRef<HTMLButtonElement, Props>(function Button({ variant = "default", size = "md", icon, className, type = "button", ...rest }, ref) {
  const cls = [s.btn, variant === "primary" && s.primary, variant === "ghost" && s.ghost, size === "sm" && s.sm, icon && s.icon, className].filter(Boolean).join(" ");
  return <button ref={ref} type={type} className={cls} {...rest} />;
});
