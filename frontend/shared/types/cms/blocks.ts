import type { CTAButton, Heading, Image } from './common'

export interface HeroBlock {
  type: 'hero'
  id: string
  value: {
    badge: string
    title: {
      title: string
      highlight_text: string
    }
    description: string
    cta_button: CTAButton
  }
}

export interface VisionMisionBlock {
  type: 'vision_mision'
  id: string
  value: {
    background: string
    vision: {
      title: string
      description: string
      icon: string
    }
    mision: {
      title: string
      description: string
      icon: string
    }
  }
}

export interface BenefitsBlock {
  type: 'benefits'
  id: string
  value: {
    background: string
    heading: Heading

    items: {
      title: string
      description: string
      icon: string
    }[]
  }
}

export interface BenefitsBlock {
  type: 'benefits'
  id: string
  value: {
    background: string
    heading: Heading

    items: {
      title: string
      description: string
      icon: string
    }[]
  }
}

export interface TeamBlock {
  type: 'team'
  id: string
  value: {
    background: string
    heading: Heading

    members: {
      name: string
      role: string
      image: Image
      description: string
    }[]
  }
}

export interface FeatureHighlightBlock {
  type: 'feature_highlight'
  id: string
  value: {
    background: string
    imagen: Image
    title: {
      title: string
      highlight_text: string
    }
    description: string
    items: {
      list_icon: string
      items: {
        text: string
      }[]
    }
    badge: {
      text: string
      status: string
      icon: string
    }
  }
}

export interface CTASectionBlock {
  type: 'cta_section'
  id: string
  value: {
    background: string
    heading: Heading
    cta_button: CTAButton
  }
}

export type BlockType =
  | 'hero'
  | 'vision_mision'
  | 'benefits'
  | 'team'
  | 'feature_highlight'
  | 'cta_section'

export type StreamBlock =
  | HeroBlock
  | VisionMisionBlock
  | BenefitsBlock
  | TeamBlock
  | FeatureHighlightBlock
  | CTASectionBlock