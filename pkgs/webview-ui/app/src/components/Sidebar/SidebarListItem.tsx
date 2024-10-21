import {Typography} from '@/src/components/Typography'

interface SidebarListItem {
    title:string;
    delegateClick: () => void;
}

export const SidebarListItem = (props: SidebarListItem) =>{
    const {title} = props;

    return <li class="sidebar__list__item">
            <Typography classes='sidebar__list__content' tag='span' hierarchy='body' size='default' weight='normal' color="primary" inverted={true}>{title}</Typography>              
         </li>
}