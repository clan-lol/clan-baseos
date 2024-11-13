import { JSX } from "solid-js";

interface FormSectionProps {
  children: JSX.Element;
}
export const FormSection = (props: FormSectionProps) => {
  return <div class="p-2">{props.children}</div>;
};
