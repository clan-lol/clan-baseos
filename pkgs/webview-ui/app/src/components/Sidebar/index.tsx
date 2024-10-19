import { type JSX } from "solid-js"
import { List } from "../Helpers";

import {SidebarHeader} from "./SidebarHeader"
import "./css/sidebar.css";
import { SidebarListItem } from "./SidebarListItem";

export const SidebarSection = (props:{children: JSX.Element}) =>{
    const {children} = props
    return <div class="sidebar__section">{children}</div>
}

export const Sidebar = () => {
 return (
    <div class="sidebar bg-opacity-95">
        <SidebarHeader/>
        <div class="sidebar__body">
            <SidebarSection>    
                <List gapSize="small">
                    <SidebarListItem title="test" delegateClick={()=>{}}/>
                    <SidebarListItem title="test" delegateClick={()=>{}}/>
                    <SidebarListItem title="test" delegateClick={()=>{}}/>
                    <SidebarListItem title="test" delegateClick={()=>{}}/>
                </List>
            </SidebarSection>
            <SidebarSection>    
                <List gapSize="small">
                    <SidebarListItem title="test" delegateClick={()=>{}}/>
                    <SidebarListItem title="test" delegateClick={()=>{}}/>
                    <SidebarListItem title="test" delegateClick={()=>{}}/>
                    <SidebarListItem title="test" delegateClick={()=>{}}/>
                </List>
            </SidebarSection>        
        </div>
    </div>
 )   
}