import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import React from 'react'

describe('shell', () => {
  it('has a portfolio app name', () => {
    render(<h1>ServiceFlow AI</h1>)
    expect(screen.getByText('ServiceFlow AI')).toBeTruthy()
  })
})
