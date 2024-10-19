import {SidebarFlyout} from './SidebarFlyout'

export const SidebarHeader = ()=>{
    return <header class="sidebar__header">
        <div class="sidebar__header__inner">
            <div class="sidebar__profile">P</div>
            <h3 class="sidebar__title">Paul's Clan</h3>
        </div>
        <SidebarFlyout/>
    </header>
}