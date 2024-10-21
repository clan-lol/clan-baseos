import {SidebarFlyout} from './SidebarFlyout'
import {Typography} from '@/src/components/Typography'

interface SidebarHeader {
    clanName?: string
}

export const SidebarHeader = (props:SidebarHeader)=>{
    const {clanName} = props
    
    return <header class="sidebar__header">
        <div class="sidebar__header__inner">
            <div class="sidebar__profile">P</div>
            <Typography classes='sidebar__title' tag='h3' hierarchy='body' size='default' weight='medium' color='primary' inverted={true}>{clanName || 'Untitled'}</Typography>
        </div>
        <SidebarFlyout/>
    </header>
}