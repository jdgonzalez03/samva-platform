import { expect, type Page } from '@playwright/test'

export const E2E_USER = {
  email: process.env.E2E_USER_EMAIL ?? 'juan.perez@email.com',
  password: process.env.E2E_USER_PASSWORD ?? 'E2eSmoke_2026!',
}

/**
 * Every UI string the specs select by (roles, toasts, labels).
 * This map is the locale seam: when i18n lands, only these values change
 * (to the Spanish defaults) — never the spec logic.
 */
export const T = {
  // login page
  signIn: 'Iniciar sesión',
  loginSuccessToast: 'Bienvenido de nuevo',
  loginErrorToast: 'Error al iniciar sesión',
  emailValidation: 'Ingresa un correo electrónico válido',
  // sidebar user dropdown (trigger shows the user's display name;
  // last_name is stable — first_name is edited by profile.spec.ts)
  userMenu: 'Pérez',
  // seeded farmer has no avatar, so the trigger falls back to their initials
  userDisplayName: 'Juan Pérez',
  userInitials: 'JP',
  logout: 'Cerrar sesión',
  // profile page
  firstName: 'Nombre',
  saveChanges: 'Guardar cambios',
  profileUpdatedToast: 'Perfil actualizado',
  changeAvatar: 'Cambiar foto de perfil',
  profileLoadError: 'No pudimos cargar tu perfil. Inténtalo de nuevo.',
  retry: 'Reintentar',
  // sidebar profile fallback
  profileUnavailable: 'Perfil no disponible.',
  // farm switcher + dashboard plot count (seed: juan.perez owns both farms,
  // 2 plots each; farms are ordered by name so El Tesoro is the default)
  farmFirst: 'Finca El Tesoro',
  farmSecond: 'Finca San Vicente',
  plotCount: '2 lotes',
  farmsUnavailable: 'Fincas no disponibles.',
  plotsLoadError: 'No se pudieron cargar los lotes.',
  // error page (error.vue)
  errorTitle: '404 — Página no encontrada',
  errorHeading: 'Página no encontrada',
  backHome: 'Volver al inicio',
}

/** English strings + switcher labels used only by the i18n specs. */
export const T_EN = {
  signIn: 'Sign in',
  loginTitle: 'Sign in',
  loginHeading: 'Welcome back',
  logout: 'Log out',
  profileLink: 'Profile',
  errorTitle: '404 — Page not found',
  errorHeading: 'Page not found',
  backHome: 'Back to home',
}

export const SWITCHER = {
  loginTrigger: 'Cambiar idioma',
  dashboardSubmenu: 'Idioma',
  spanish: 'Español',
  english: 'English',
}

/**
 * Navigates and waits for Vue hydration: interacting with a form before
 * hydration triggers a native (full-page) submit instead of the Vue handler.
 */
export async function gotoHydrated(page: Page, path: string): Promise<void> {
  await page.goto(path)
  await page.waitForFunction(() => {
    const root = document.querySelector('#__nuxt') as { __vue_app__?: unknown } | null
    return Boolean(root?.__vue_app__)
  })
}

/**
 * Logs in through the real login form and waits for the dashboard.
 * Credentials default to E2E_USER (overridable via E2E_USER_EMAIL /
 * E2E_USER_PASSWORD env vars).
 */
export async function loginAs(
  page: Page,
  email: string = E2E_USER.email,
  password: string = E2E_USER.password,
): Promise<void> {
  await gotoHydrated(page, '/login')
  await page.locator('input[type="email"]').fill(email)
  await page.locator('input[type="password"]').fill(password)
  await page.locator('button[type="submit"]').click()
  await expect(page).toHaveURL(/\/dashboard/)
}
