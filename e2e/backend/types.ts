export interface CTAButton {
  text: string
  icon: string
  url: string
}

export interface TitleBlock {
  title: string
  highlight_text: string
}

export interface Heading {
  title: string
  text: string
}

export interface Image {
  id: number
  title: string
  url: string
  width: number
  height: number
}

export interface HeroValue {
  badge: string
  title: TitleBlock
  description: string
  cta_button: CTAButton
}

export interface VisionMisionValue {
  background: string
  vision: { title: string; description: string; icon: string }
  mision: { title: string; description: string; icon: string }
}

export interface TwoColumnsContentValue {
  background: string
  left_column: Heading
  right_column: Heading
}

export interface BenefitItem {
  title: string
  description: string
  icon: string
}

export interface BenefitsValue {
  background: string
  heading: Heading
  items: BenefitItem[]
}

export interface Member {
  name: string
  role: string
  image: Image | null
  description: string
}

export interface TeamValue {
  background: string
  heading: Heading
  members: Member[]
}

export interface FeatureHighlightValue {
  background: string
  imagen: Image | null
  title: TitleBlock
  description: string
  items: { list_icon: string; items: { text: string }[] }
  badge: { text: string; status: string; icon: string }
}

export interface CTASectionValue {
  background: string
  heading: Heading
  cta_button: CTAButton
}

export type BlockValue =
  | HeroValue
  | VisionMisionValue
  | TwoColumnsContentValue
  | BenefitsValue
  | TeamValue
  | FeatureHighlightValue
  | CTASectionValue

export interface StreamBlock {
  type: string
  id: string
  value: BlockValue
}

export interface LandingData {
  title: string
  body: StreamBlock[]
}
