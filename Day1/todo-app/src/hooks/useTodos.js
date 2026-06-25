import { useState, useEffect } from 'react'
import { supabase } from '../lib/supabase'

export function useTodos() {
  const [todos, setTodos] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetchTodos()
  }, [])

  async function fetchTodos() {
    setLoading(true)
    setError(null)
    try {
      const { data, error } = await supabase
        .from('todos')
        .select('*')
        .order('created_at', { ascending: false })
      if (error) throw error
      setTodos(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function addTodo(title) {
    if (!title.trim()) return
    try {
      const { data, error } = await supabase
        .from('todos')
        .insert([{ title: title.trim(), completed: false }])
        .select()
        .single()
      if (error) throw error
      setTodos(prev => [data, ...prev])
    } catch (err) {
      setError(err.message)
    }
  }

  async function toggleTodo(id) {
    const todo = todos.find(t => t.id === id)
    if (!todo) return
    try {
      const { error } = await supabase
        .from('todos')
        .update({ completed: !todo.completed })
        .eq('id', id)
      if (error) throw error
      setTodos(prev => prev.map(t => t.id === id ? { ...t, completed: !t.completed } : t))
    } catch (err) {
      setError(err.message)
    }
  }

  async function deleteTodo(id) {
    try {
      const { error } = await supabase
        .from('todos')
        .delete()
        .eq('id', id)
      if (error) throw error
      setTodos(prev => prev.filter(t => t.id !== id))
    } catch (err) {
      setError(err.message)
    }
  }

  async function updateTodo(id, title) {
    if (!title.trim()) return
    try {
      const { error } = await supabase
        .from('todos')
        .update({ title: title.trim() })
        .eq('id', id)
      if (error) throw error
      setTodos(prev => prev.map(t => t.id === id ? { ...t, title: title.trim() } : t))
    } catch (err) {
      setError(err.message)
    }
  }

  return { todos, loading, error, addTodo, toggleTodo, deleteTodo, updateTodo }
}
