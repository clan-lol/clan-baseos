import {createSignal} from 'solid-js'

import {Typography} from '@/src/components/Typography'
import {SidebarFlyout} from './SidebarFlyout'

interface SidebarHeader {
    clanName?: string
}

export const SidebarHeader = (props:SidebarHeader)=>{
    const {clanName} = props;

    const [showFlyout, toggleFlyout] = createSignal(false)

    function handleClick(){
        toggleFlyout(!showFlyout())
    }
    
    return <header class="sidebar__header">
        <div onClick={handleClick} class="sidebar__header__inner">
            <div class={`sidebar__profile ${showFlyout() ? 'sidebar__profile--flyout' : ''}`}>
                <Typography classes='sidebar__title' tag='span' hierarchy='title' size='m' weight='bold' color='primary' inverted={!showFlyout()}>
                    {clanName?.slice(0,1) || 'U'}
                </Typography>    
            </div>
            <Typography classes='sidebar__title' tag='h3' hierarchy='body' size='default' weight='medium' color='primary' inverted={true}>{clanName || 'Untitled'}</Typography>
        </div>
        { showFlyout() &&
            <SidebarFlyout/>
        }
        
    </header>
}