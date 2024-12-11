import { JSX } from "solid-js";
import { Typography } from "../components/Typography";
import { BackButton } from "../components/BackButton";

interface HeaderProps {
  title: string;
  toolbar?: JSX.Element;
  showBack?: boolean;
}
export const Header = (props: HeaderProps) => {
  return (
    <div class="navbar border-b px-6 py-4 border-def-3">
      <div class="flex-none">
        {props.showBack && <BackButton />}
        <span class="tooltip tooltip-bottom lg:hidden" data-tip="Menu">
          <label
            class="btn btn-square btn-ghost drawer-button"
            for="toplevel-drawer"
          >
            <span class="material-icons">menu</span>
          </label>
        </span>
      </div>
      <div class="flex-1">
        <Typography hierarchy="title" size="m" weight="medium" class="">
          {props.title}
        </Typography>
      </div>
      <div class="flex-none items-center justify-center gap-3">
        {props.toolbar}
      </div>
    </div>
  );
};
