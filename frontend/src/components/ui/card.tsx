import React from 'react'

export const Card: React.FC<{className?:string, children: React.ReactNode}> = ({className='', children}) => (
  <div className={`card ${className}`}>{children}</div>
)

export const CardHeader: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div className="mb-2">{children}</div>
)

export const CardTitle: React.FC<{children: React.ReactNode}> = ({children}) => (
  <div className="text-lg font-semibold">{children}</div>
)

export const CardContent: React.FC<{children: React.ReactNode, className?:string}> = ({children, className=''}) => (
  <div className={`space-y-2 ${className}`}>{children}</div>
)