import {type JSX} from 'solid-js'
import {Dynamic} from 'solid-js/web'

import './css/typography.css'

type Hierarchy = 'body' | 'title' | 'headline'
type Size = 'default' | 'xs' | 's' | 'm' | 'l'
type Color = 'primary' | 'secondary' | 'tertiary'
type Weight = 'normal' | 'medium' | 'bold'
type Tag = 'span' | 'p' | 'h1' | 'h2' |'h3'| 'h4'  

interface Typography {
    hierarchy: Hierarchy
    weight: Weight
    color: Color
    inverted: boolean
    size: Size
    tag: Tag
    children: JSX.Element
    classes?: string
}

export const Typography = (props: Typography) => {
    const {size, color, inverted, hierarchy, weight, tag, children, classes} = props
    
    return <Dynamic component={tag} class={`${classes? classes + ' ' : ''} fnt-${hierarchy}-${size} fnt-clr-${color} fnt-clr--${inverted ? 'inverted' : 'default'} fnt-${weight}`}>{children}</Dynamic>
}