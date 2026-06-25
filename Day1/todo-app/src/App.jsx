import { useState, useMemo } from 'react'
import { useTodos } from './hooks/useTodos'
import { TodoInput } from './components/TodoInput'
import { TodoList } from './components/TodoList'
import { TodoFilter } from './components/TodoFilter'
import './App.css'

export default function App() {
  const { todos, loading, error, addTodo, toggleTodo, deleteTodo, updateTodo } = useTodos()
  const [filter, setFilter] = useState('all')

  const filteredTodos = useMemo(() => {
    if (filter === 'active') return todos.filter(t => !t.completed)
    if (filter === 'completed') return todos.filter(t => t.completed)
    return todos
  }, [todos, filter])

  const counts = useMemo(() => ({
    all: todos.length,
    active: todos.filter(t => !t.completed).length,
    completed: todos.filter(t => t.completed).length,
  }), [todos])

  return (
    <div className="app">
      <div className="todo-container">
        <h1 className="todo-heading">Todo App</h1>

        <TodoInput onAdd={addTodo} />

        <TodoFilter filter={filter} onFilterChange={setFilter} counts={counts} />

        {loading && <p className="todo-loading">불러오는 중...</p>}
        {error && <p className="todo-error">오류: {error}</p>}

        {!loading && (
          <TodoList
            todos={filteredTodos}
            onToggle={toggleTodo}
            onDelete={deleteTodo}
            onUpdate={updateTodo}
          />
        )}

        {counts.completed > 0 && (
          <div className="todo-footer">
            <span>{counts.completed}개 완료됨</span>
          </div>
        )}
      </div>
    </div>
  )
}
