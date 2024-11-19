import {List} from '@/src/components/Helpers' 
import {SidebarListItem} from '../SidebarListItem'

export const SidebarFlyout= () =>{
    return <div class="sidebar__flyout">
        <div class="sidebar__flyout__inner">
            <List gapSize='small'>
                <SidebarListItem href='/settings' title='Settings' />
            </List>
        </div>
    </div>
}