import React from 'react';

/**
 * Website Clone - React Starter Template
 *
 * Replace placeholder content with extracted site content.
 * Update styles in styles.module.css with extracted theme values.
 */

function Header() {
    return (
        <header className="site-header">
            <div className="container">
                <a href="/" className="logo">
                    {/* Replace with extracted logo */}
                    <img src="/images/logo.png" alt="Site Name" width={200} height={60} />
                </a>
                <nav className="main-nav">
                    <ul>
                        <li><a href="/">Home</a></li>
                        <li><a href="/about">About</a></li>
                        <li><a href="/services">Services</a></li>
                        <li><a href="/contact">Contact</a></li>
                    </ul>
                </nav>
            </div>
        </header>
    );
}

function Hero() {
    return (
        <section className="hero">
            <h1>Page Heading</h1>
            <p>Introductory text goes here. Replace with extracted content.</p>
        </section>
    );
}

function ContentSection({ title, children }) {
    return (
        <section className="content-section">
            <h2>{title}</h2>
            {children}
        </section>
    );
}

function CTASection() {
    return (
        <section className="cta-section">
            <h2>Call to Action</h2>
            <p>Encourage the visitor to take action.</p>
            <a href="/contact" className="btn-cta">Get Started</a>
        </section>
    );
}

function Footer() {
    return (
        <footer className="site-footer">
            <div className="container">
                <p>&copy; {new Date().getFullYear()} Site Name. All rights reserved.</p>
            </div>
        </footer>
    );
}

export default function App() {
    return (
        <>
            <Header />
            <main className="site-main">
                <div className="container">
                    <Hero />
                    <ContentSection title="Section Heading">
                        <p>
                            Section content goes here. Replace with extracted
                            content from the original site.
                        </p>
                    </ContentSection>
                    <CTASection />
                </div>
            </main>
            <Footer />
        </>
    );
}
