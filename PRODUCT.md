# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

The product is a local Python MCP server; its public reading surface is a GitHub README, not a hosted application.

## Users

University students who use Microsoft Teams Educación and want to consult course tasks, announcements and materials from an MCP assistant. Each student installs it on their own Windows, macOS or Linux computer.

## Product Purpose

Make the student's existing Teams content available through eight MCP tools. Success means installing locally, signing in with the student's own account and querying real course content.

## Positioning

A dedicated local Chromium reads the rendered Teams interface. It requires no Entra app registration or Microsoft Graph permission grant. Institutional access restrictions still apply.

## Operating Context

Python 3.11+, local stdio MCP client, interactive Microsoft sign-in and MFA. The browser profile lives outside the repository. Sharing the project never shares a session.

## Capabilities and Constraints

Lists courses, assignments by status, assignment instructions, General-channel announcements, folders and documents. Extracts DOCX, PPTX and PDF text. No messaging, submission or document editing tools. Virtualized lists can be partial. UI updates can require maintenance. Linux was tested with a real account; Windows/macOS have installers and an automated CI matrix.

## Brand Commitments

Name: Teams Facultad MCP. Spanish, approachable language for university peers. Independent project, no Microsoft or university affiliation. Public repository owner: Matias-Sanmiguel. The user requested Impeccable for the branding.

## Evidence on Hand

Automated tests, a real authenticated Teams session tested locally, synthetic browser fixtures, installers, source archive builder and GitHub Actions workflow. Public artifacts exclude private account content and browser data.

## Product Principles

- Each person keeps control of their own account and session.
- Show incomplete results and original dates honestly.
- Make installation reproducible and the code easy to share.
- Prefer clear instructions and real capabilities over marketing claims.
