<template>
  <router-view />
</template>

<script setup>
// 这里可以做一些全局的初始化逻辑，目前保持干净即可
</script>

<style>
/* 基础样式重置，确保满屏 */
html, body, #app {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: #f5f7fa;
}
</style>