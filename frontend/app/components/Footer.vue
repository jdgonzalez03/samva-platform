<script setup lang="ts">
import Logo from '~/components/Logo.vue'
</script>

<template>
  <UFooter class="bg-black p-8">
    <template #left>
      <div class="flex flex-col items-start">
        <Logo :is-bg-white="false" />
        <p class="text-muted text-sm mt-2 max-w-md">
          Sistemas de Apoyo al Monitoreo de Variables Agrícolas. Innovación tecnológica para un campo más productivo y
          sostenible.
        </p>
        <div class="flex items-center space-x-4 mt-4">
          <UIcon name="i-lucide-github" class="text-primary size-6" />
          <UIcon name="i-lucide-linkedin" class="text-primary size-6" />
        </div>
      </div>
    </template>
    <template #right>
      <div class="flex flex-col w-100 p-4">
        <h3 class="text-white text-base font-semibold mb-2">Contacto</h3>

        <div class="grid grid-cols-1 gap-3 text-sm">
          <div class="flex items-center space-x-2">
            <UIcon name="i-lucide-mail" class="text-primary size-4" />
            <a href="mailto:info@samva.cl" class="text-white hover:text-primary">
              info@samva.cl
            </a>
          </div>

          <div class="flex items-center space-x-2">
            <UIcon name="i-lucide-phone" class="text-primary size-4" />
            <a href="tel:+56912345678" class="text-white hover:text-primary">
              +56 9 1234 5678
            </a>
          </div>

          <div class="flex items-center space-x-2">
            <UIcon name="i-lucide-map-pin" class="text-primary size-4" />
            <span class="text-white">Santiago, Chile</span>
          </div>
        </div>
      </div>
    </template>
    <template #bottom>
      <hr class="border-gray-700 mb-4">
      <p class="text-muted text-sm text-center">
        &copy; S.A.M.V.A. {{ new Date().getFullYear() }}. Todos los derechos reservados.
      </p>
    </template>
  </UFooter>
</template>
