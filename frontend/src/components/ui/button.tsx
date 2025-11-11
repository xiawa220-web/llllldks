import React from 'react'

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: 'default'|'outline'|'ghost' }

export const Button: React.FC<Props> = ({ className='', variant='default', children, ...rest }) => {
  const base = 'inline-flex items-center justify-center rounded-xl font-semibold transition-colors'
  const sizes = 'px-4 py-2 text-sm'
  const variants: Record<string,string> = {
    default: 'bg-[rgb(var(--primary))] text-white hover:brightness-105',
    outline: 'border border-[rgb(var(--border))] text-[rgb(var(--foreground))] bg-white hover:bg-gray-50',
    ghost: 'text-[rgb(var(--foreground))] hover:bg-gray-50'
  }
  return <button className={`${base} ${sizes} ${variants[variant]} ${className}`} {...rest}>{children}</button>
}