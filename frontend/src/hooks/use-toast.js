"use client";
// Inspired by react-hot-toast library
import * as React from "react"

const TOAST_LIMIT = 1
const TOAST_REMOVE_DELAY = 1000000

const actionTypes = {
  ADD_TOAST: "ADD_TOAST",
  UPDATE_TOAST: "UPDATE_TOAST",
  DISMISS_TOAST: "DISMISS_TOAST",
  REMOVE_TOAST: "REMOVE_TOAST"
}

let count = 0

function genId() {
  count = (count + 1) % Number.MAX_SAFE_INTEGER
  return count.toString();
}

const toastTimeouts = new Map()

const addToRemoveQueue = (toastId) => {
  if (toastTimeouts.has(toastId)) {
    return
  }

  const timeout = setTimeout(() => {
    toastTimeouts.delete(toastId)
    dispatch({
      type: "REMOVE_TOAST",
      toastId: toastId,
    })
  }, TOAST_REMOVE_DELAY)

  toastTimeouts.set(toastId, timeout)
}

function addToast(state, action) {
  return {
    ...state,
    toasts: [action.toast, ...state.toasts].slice(0, TOAST_LIMIT),
  };
}

function updateToast(state, action) {
  return {
    ...state,
    toasts: state.toasts.map((t) =>
      t.id === action.toast.id ? { ...t, ...action.toast } : t),
  };
}

function dismissToast(state, action) {
  const { toastId } = action

  if (toastId) {
    addToRemoveQueue(toastId)
  } else {
    state.toasts.forEach((toast) => {
      addToRemoveQueue(toast.id)
    })
  }

  return {
    ...state,
    toasts: state.toasts.map((t) =>
      t.id === toastId || toastId === undefined
        ? {
            ...t,
            open: false,
          }
        : t),
  };
}

function removeToast(state, action) {
  if (action.toastId === undefined) {
    return {
      ...state,
      toasts: [],
    }
  }
  return {
    ...state,
    toasts: state.toasts.filter((t) => t.id !== action.toastId),
  };
}

export function reducer(state, action) {
  switch (action.type) {
    case "ADD_TOAST":
      return addToast(state, action);

    case "UPDATE_TOAST":
      return updateToast(state, action);

    case "DISMISS_TOAST":
      return dismissToast(state, action);

    case "REMOVE_TOAST":
      return removeToast(state, action);

    default:
      return state;
  }
}

const listeners = []

let memoryState = { toasts: [] }

function dispatch(action) {
  memoryState = reducer(memoryState, action)
  listeners.forEach((listener) => {
    listener(memoryState)
  })
}

function subscribeToastListener(listener) {
  listeners.push(listener)
  return () => {
    const index = listeners.indexOf(listener)
    if (index > -1) {
      listeners.splice(index, 1)
    }
  };
}

function toast({
  ...props
}) {
  const id = genId()

  const update = (props) =>
    dispatch({
      type: "UPDATE_TOAST",
      toast: { ...props, id },
    })
  const dismiss = () => dispatch({ type: "DISMISS_TOAST", toastId: id })

  dispatch({
    type: "ADD_TOAST",
    toast: {
      ...props,
      id,
      open: true,
      onOpenChange: (open) => {
        if (!open) dismiss()
      },
    },
  })

  return {
    id: id,
    dismiss,
    update,
  }
}

function useToast() {
  const [state, setState] = React.useState(memoryState)

  React.useEffect(() => {
    return subscribeToastListener(setState);
  }, [setState, subscribeToastListener])

  return {
    ...state,
    toast,
    dismiss: (toastId) => dispatch({ type: "DISMISS_TOAST", toastId }),
  };
}

export { useToast, toast }
