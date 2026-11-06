<script setup>
import { javascript } from '@codemirror/lang-javascript'
import { json } from '@codemirror/lang-json'
import { Compartment, EditorState } from '@codemirror/state'
import { EditorView } from '@codemirror/view'
import { basicSetup } from 'codemirror'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  language: { type: String, default: 'javascript' }, // javascript | json
  readonly: { type: Boolean, default: false },
  label: { type: String, required: true },
})
const model = defineModel({ type: String, default: '' })

const host = ref(null)
const editable = new Compartment()
let view = null

function editableExtension() {
  return editable.of([EditorState.readOnly.of(props.readonly), EditorView.editable.of(!props.readonly)])
}

onMounted(() => {
  view = new EditorView({
    parent: host.value,
    state: EditorState.create({
      doc: model.value,
      extensions: [
        basicSetup,
        props.language === 'json' ? json() : javascript(),
        editableExtension(),
        EditorView.contentAttributes.of({ 'aria-label': props.label }),
        EditorView.lineWrapping,
        EditorView.updateListener.of((update) => {
          if (update.docChanged) model.value = update.state.doc.toString()
        }),
      ],
    }),
  })
})

watch(model, (value) => {
  if (view && value !== view.state.doc.toString()) {
    view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: value } })
  }
})

watch(
  () => props.readonly,
  () => view?.dispatch({ effects: editable.reconfigure(editableExtension()) }),
)

onBeforeUnmount(() => view?.destroy())
</script>

<template>
  <div ref="host" class="code-editor overflow-hidden rounded-control border border-line bg-surface text-sm"></div>
</template>

<style scoped>
.code-editor {
  height: 100%;
}
.code-editor :deep(.cm-editor) {
  height: 100%;
}
.code-editor :deep(.cm-editor.cm-focused) {
  outline: 2px solid var(--color-brand-500);
  outline-offset: -2px;
}
.code-editor :deep(.cm-scroller) {
  overflow: auto;
}
</style>
