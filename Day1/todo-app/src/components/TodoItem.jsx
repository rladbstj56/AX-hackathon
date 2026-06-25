import { useState } from 'react'

export function TodoItem({ todo, onToggle, onDelete, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [editValue, setEditValue] = useState(todo.title)

  function handleEditSubmit(e) {
    e.preventDefault()
    if (!editValue.trim()) return
    onUpdate(todo.id, editValue)
    setEditing(false)
  }

  function handleKeyDown(e) {
    if (e.key === 'Escape') {
      setEditValue(todo.title)
      setEditing(false)
    }
  }

  return (
    <li className={`todo-item${todo.completed ? ' completed' : ''}`}>
      <input
        type="checkbox"
        className="todo-checkbox"
        checked={todo.completed}
        onChange={() => onToggle(todo.id)}
      />
      {editing ? (
        <form className="todo-edit-form" onSubmit={handleEditSubmit}>
          <input
            type="text"
            className="todo-edit-input"
            value={editValue}
            onChange={e => setEditValue(e.target.value)}
            onKeyDown={handleKeyDown}
            autoFocus
          />
          <button type="submit" className="todo-save-btn">저장</button>
          <button
            type="button"
            className="todo-cancel-btn"
            onClick={() => { setEditValue(todo.title); setEditing(false) }}
          >취소</button>
        </form>
      ) : (
        <>
          <span className="todo-title" onDoubleClick={() => setEditing(true)}>
            {todo.title}
          </span>
          <div className="todo-actions">
            <button className="todo-edit-btn" onClick={() => setEditing(true)}>수정</button>
            <button className="todo-delete-btn" onClick={() => onDelete(todo.id)}>삭제</button>
          </div>
        </>
      )}
    </li>
  )
}
