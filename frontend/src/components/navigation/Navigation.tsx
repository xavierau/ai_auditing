/**
 * Navigation Component
 *
 * Top navigation bar with market context and user menu.
 * Follows design system navigation pattern.
 */

import { useState } from 'react';
import { Menu, X, Sparkles, FolderOpen, Settings, LogOut, User } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { JurisdictionBadge } from '@/components';
import { cn } from '@/lib/utils';
import type { Jurisdiction } from '@/utils/market';

export interface NavigationProps {
  currentUser?: {
    name: string;
    email: string;
    tenant_name: string;
    jurisdiction?: Jurisdiction;
  };
  onNavigate?: (path: string) => void;
  onLogout?: () => void;
  className?: string;
}

interface NavItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { label: 'Projects', path: '/projects', icon: FolderOpen },
  { label: 'Generate', path: '/generate', icon: Sparkles },
  { label: 'Settings', path: '/settings', icon: Settings },
];

/**
 * Navigation - Top navigation bar
 *
 * @example
 * <Navigation
 *   currentUser={user}
 *   onNavigate={(path) => navigate(path)}
 *   onLogout={() => handleLogout()}
 * />
 */
export function Navigation({
  currentUser,
  onNavigate,
  onLogout,
  className,
}: NavigationProps) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);

  const handleNavClick = (path: string) => {
    setIsMobileMenuOpen(false);
    onNavigate?.(path);
  };

  return (
    <nav
      className={cn(
        'sticky top-0 z-50 border-b border-gray-200 bg-white shadow-sm',
        className
      )}
      aria-label="Main navigation"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => handleNavClick('/projects')}
              className="flex items-center gap-2 text-xl font-bold text-gray-900 hover:text-blue-600"
              aria-label="GenReport home"
            >
              <Sparkles className="h-6 w-6 text-blue-600" aria-hidden="true" />
              GenReport
            </button>

            {/* Jurisdiction Badge (Desktop) */}
            {currentUser?.jurisdiction && (
              <div className="hidden sm:block">
                <JurisdictionBadge jurisdiction={currentUser.jurisdiction} />
              </div>
            )}
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex md:items-center md:gap-6">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.path}
                  onClick={() => handleNavClick(item.path)}
                  className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                  aria-label={item.label}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </button>
              );
            })}
          </div>

          {/* User Menu */}
          <div className="flex items-center gap-4">
            {/* Tenant Name (Desktop) */}
            {currentUser && (
              <div className="hidden lg:block text-sm text-gray-600">
                {currentUser.tenant_name}
              </div>
            )}

            {/* User Dropdown */}
            {currentUser && (
              <div className="relative">
                <button
                  onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                  className="flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
                  aria-expanded={isUserMenuOpen}
                  aria-haspopup="true"
                  aria-label="User menu"
                >
                  <User className="h-4 w-4" aria-hidden="true" />
                  <span className="hidden sm:inline">{currentUser.name}</span>
                </button>

                {/* Dropdown Menu */}
                {isUserMenuOpen && (
                  <>
                    {/* Backdrop */}
                    <div
                      className="fixed inset-0 z-10"
                      onClick={() => setIsUserMenuOpen(false)}
                      aria-hidden="true"
                    />

                    {/* Menu */}
                    <div
                      className="absolute right-0 z-20 mt-2 w-56 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5"
                      role="menu"
                      aria-orientation="vertical"
                    >
                      <div className="border-b border-gray-100 p-4">
                        <p className="text-sm font-medium text-gray-900">{currentUser.name}</p>
                        <p className="mt-1 text-xs text-gray-600">{currentUser.email}</p>
                        <p className="mt-1 text-xs text-gray-500">{currentUser.tenant_name}</p>
                      </div>

                      <div className="py-1">
                        <button
                          onClick={() => {
                            setIsUserMenuOpen(false);
                            handleNavClick('/settings');
                          }}
                          className="flex w-full items-center gap-2 px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                          role="menuitem"
                        >
                          <Settings className="h-4 w-4" aria-hidden="true" />
                          Settings
                        </button>
                        <button
                          onClick={() => {
                            setIsUserMenuOpen(false);
                            onLogout?.();
                          }}
                          className="flex w-full items-center gap-2 px-4 py-2 text-sm text-red-700 hover:bg-red-50"
                          role="menuitem"
                        >
                          <LogOut className="h-4 w-4" aria-hidden="true" />
                          Logout
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Mobile Menu Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="md:hidden"
              aria-expanded={isMobileMenuOpen}
              aria-label="Toggle mobile menu"
            >
              {isMobileMenuOpen ? (
                <X className="h-5 w-5" aria-hidden="true" />
              ) : (
                <Menu className="h-5 w-5" aria-hidden="true" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="border-t border-gray-200 md:hidden" role="navigation">
          <div className="space-y-1 px-4 pb-3 pt-2">
            {/* Jurisdiction Badge (Mobile) */}
            {currentUser?.jurisdiction && (
              <div className="mb-3">
                <JurisdictionBadge jurisdiction={currentUser.jurisdiction} showFullName />
              </div>
            )}

            {/* Nav Items */}
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.path}
                  onClick={() => handleNavClick(item.path)}
                  className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-base font-medium text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                >
                  <Icon className="h-5 w-5" aria-hidden="true" />
                  {item.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </nav>
  );
}
