import React from 'react'

type Props = {
  label: string
  values: string[]
  onChange: (values: string[]) => void
  placeholder?: string
}

export default function ListInput({ label, values, onChange, placeholder }: Props) {
  const [text, setText] = React.useState<string>('')

  React.useEffect(() => {
    setText((values || []).join(', '))
  }, [JSON.stringify(values)])

  function onBlur() {
    const list = (text || '')
      .split(',')
      .map(s => s.trim())
      .filter(Boolean)
    onChange(list)
  }

  return (
    <label>
      {label}
      <input value={text} placeholder={placeholder} onChange={e => setText(e.target.value)} onBlur={onBlur} />
    </label>
  )
}


