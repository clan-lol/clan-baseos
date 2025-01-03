import { Component, JSX, splitProps } from "solid-js";
import ArrowBottom from "@/icons/arrow-bottom.svg";
import ArrowLeft from "@/icons/arrow-left.svg";
import ArrowRight from "@/icons/arrow-right.svg";
import ArrowTop from "@/icons/arrow-top.svg";
import Attention from "@/icons/attention.svg";
import CaretDown from "@/icons/caret-down.svg";
import CaretLeft from "@/icons/caret-left.svg";
import CaretRight from "@/icons/caret-right.svg";
import CaretUp from "@/icons/caret-up.svg";
import Checkmark from "@/icons/checkmark.svg";
import ClanIcon from "@/icons/clan-icon.svg";
import ClanLogo from "@/icons/clan-logo.svg";
import Close from "@/icons/close.svg";
import Download from "@/icons/download.svg";
import Edit from "@/icons/edit.svg";
import Expand from "@/icons/expand.svg";
import EyeClose from "@/icons/eye-close.svg";
import EyeOpen from "@/icons/eye-open.svg";
import Filter from "@/icons/filter.svg";
import Flash from "@/icons/flash.svg";
import Folder from "@/icons/folder.svg";
import Grid from "@/icons/grid.svg";
import Info from "@/icons/info.svg";
import List from "@/icons/list.svg";
import Load from "@/icons/load.svg";
import More from "@/icons/more.svg";
import Paperclip from "@/icons/paperclip.svg";
import Plus from "@/icons/plus.svg";
import Reload from "@/icons/reload.svg";
import Report from "@/icons/report.svg";
import Search from "@/icons/search.svg";
import Settings from "@/icons/settings.svg";
import Trash from "@/icons/trash.svg";
import Update from "@/icons/update.svg";
import Warning from "@/icons/warning.svg";

const icons = {
  ArrowBottom,
  ArrowLeft,
  ArrowRight,
  ArrowTop,
  Attention,
  CaretDown,
  CaretLeft,
  CaretRight,
  CaretUp,
  Checkmark,
  ClanIcon,
  ClanLogo,
  Close,
  Download,
  Edit,
  Expand,
  EyeClose,
  EyeOpen,
  Filter,
  Flash,
  Folder,
  Grid,
  Info,
  List,
  Load,
  More,
  Paperclip,
  Plus,
  Reload,
  Report,
  Search,
  Settings,
  Trash,
  Update,
  Warning,
};

export type IconVariant = keyof typeof icons;

interface IconProps extends JSX.SvgSVGAttributes<SVGElement> {
  icon: IconVariant;
}

const Icon: Component<IconProps> = (props) => {
  const [local, iconProps] = splitProps(props, ["icon"]);

  const IconComponent = icons[local.icon];
  return IconComponent ? (
    <IconComponent
      width={16}
      height={16}
      viewBox="0 0 48 48"
      // @ts-expect-error: dont know, fix this type nit later
      ref={iconProps.ref}
      {...iconProps}
    />
  ) : null;
};

export default Icon;
