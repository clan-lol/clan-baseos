import { type JSX } from "solid-js"
import { activeURI } from "@/src/App"
import { createQuery } from "@tanstack/solid-query";
import { callApi } from "@/src/api";

import { List } from "../Helpers";

import {SidebarHeader} from "./SidebarHeader"
import "./css/sidebar.css";
import { SidebarListItem } from "./SidebarListItem";

export const SidebarSection = (props:{children: JSX.Element}) =>{
    const {children} = props
    return <div class="sidebar__section">{children}</div>
}

export const Sidebar = () => {
    const query = createQuery(() => ({
        queryKey: [activeURI(), "meta"],
        queryFn: async () => {
                const curr = activeURI();
                if (curr) {
                const result = await callApi("show_clan_meta", { uri: curr });
                
                if (result.status === "error") throw new Error("Failed to fetch data");
                
                return result.data;
            }
        },
    }));

 return (
    <div class="sidebar bg-opacity-95">
        <SidebarHeader clanName={query.data?.name}/>
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