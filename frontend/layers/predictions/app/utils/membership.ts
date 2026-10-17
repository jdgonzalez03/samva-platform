import type {
  FuzzyVariableDefinition,
  MembershipFunction,
} from '../types/predictions'

const rising = (x: number, start: number, peak: number): number =>
  peak === start ? 1 : (x - start) / (peak - start)

const falling = (x: number, peak: number, end: number): number =>
  end === peak ? 1 : (end - x) / (end - peak)

// Same piecewise-linear shapes as skfuzzy's `trapmf`/`trimf`: a triangle is a
// trapezoid whose top is a single point.
export const membershipAt = (mf: MembershipFunction, x: number): number => {
  const [a, b, c, d] =
    mf.shape === 'tri'
      ? [mf.points[0]!, mf.points[1]!, mf.points[1]!, mf.points[2]!]
      : (mf.points as [number, number, number, number])

  if (x < a || x > d) return 0
  if (x < b) return rising(x, a, b)
  if (x <= c) return 1
  return falling(x, c, d)
}

export interface MembershipSample {
  x: number
  terms: Record<string, number>
  // Mamdani aggregation: each term clipped at its activation, then the max.
  activated: number
}

export const sampleOutput = (
  variable: FuzzyVariableDefinition,
  activation: Record<string, number>,
  step = 0.25,
): MembershipSample[] => {
  const [low, high] = variable.bounds
  const samples: MembershipSample[] = []

  for (let x = low; x <= high + 1e-9; x += step) {
    const terms = Object.fromEntries(
      Object.entries(variable.terms).map(([term, mf]) => [
        term,
        membershipAt(mf, x),
      ]),
    )
    const activated = Math.max(
      0,
      ...Object.entries(terms).map(([term, degree]) =>
        Math.min(degree, activation[term] ?? 0),
      ),
    )
    samples.push({ x, terms, activated })
  }
  return samples
}
