<template>
  <div>{{ msg }}</div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

const msg = ref('hi');

function greet() {
  return msg.value;
}
</script>
