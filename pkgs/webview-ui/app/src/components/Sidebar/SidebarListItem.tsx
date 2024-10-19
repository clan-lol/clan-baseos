interface SidebarListItem {
    title:string;
    delegateClick: () => void;
}

export const SidebarListItem = (props: SidebarListItem) =>{
    const {title} = props;

    return <li class="sidebar__list__item">
        <span class="sidebar__list__content">{title}</span></li>
}