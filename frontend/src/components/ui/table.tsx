import React from 'react'

export const Table: React.FC<{children: React.ReactNode, className?:string}> = ({children, className=''}) => (
  <table className={`w-full border-collapse ${className}`}>{children}</table>
)
export const THead: React.FC<{children: React.ReactNode}> = ({children}) => (
  <thead className="text-sm"><tr>{children}</tr></thead>
)
export const TH: React.FC<{children: React.ReactNode}> = ({children}) => (
  <th className="border p-2 text-left">{children}</th>
)
export const TBody: React.FC<{children: React.ReactNode}> = ({children}) => (
  <tbody>{children}</tbody>
)
export const TR: React.FC<{children: React.ReactNode}> = ({children}) => (
  <tr>{children}</tr>
)
export const TD: React.FC<{children: React.ReactNode}> = ({children}) => (
  <td className="border p-2">{children}</td>
)