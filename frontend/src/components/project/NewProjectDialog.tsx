/**
 * NewProjectDialog Component
 *
 * Modal dialog for creating a new project with form validation.
 */

import { useState } from 'react';
import { useCreateProject } from '@/hooks/useProjects';
import { useClients, useCreateClient } from '@/hooks/useClients';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';
import type { CreateProjectRequest } from '@/services/projects';
import type { Jurisdiction } from '@/utils/market';
import type { Currency } from '@/utils/currency';

export interface NewProjectDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function NewProjectDialog({ open, onOpenChange }: NewProjectDialogProps) {
  const createProject = useCreateProject();
  const createClient = useCreateClient();
  const { data: clients = [], isLoading: clientsLoading } = useClients();

  const [showNewClientForm, setShowNewClientForm] = useState(false);
  const [newClientName, setNewClientName] = useState('');

  const [formData, setFormData] = useState<CreateProjectRequest>({
    project_name: '',
    client_id: 0, // Will be set when client is selected
    jurisdiction: 'HK',
    currency: 'HKD',
    financial_year_end: new Date().toISOString().split('T')[0],
    entity_type: '',
    description: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const handleCreateClient = async () => {
    if (!newClientName.trim()) {
      setErrors({ ...errors, client: 'Client name is required' });
      return;
    }

    try {
      const newClient = await createClient.mutateAsync({
        company_name: newClientName,
      });

      // Select the newly created client
      setFormData({ ...formData, client_id: newClient.id });
      setShowNewClientForm(false);
      setNewClientName('');
      setErrors({ ...errors, client: '' });
    } catch (error) {
      console.error('Failed to create client:', error);
      setErrors({ ...errors, client: 'Failed to create client' });
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Basic validation
    const newErrors: Record<string, string> = {};
    if (!formData.project_name.trim()) {
      newErrors.project_name = 'Project name is required';
    }
    if (!formData.client_id || formData.client_id === 0) {
      newErrors.client = 'Please select a client';
    }
    if (!formData.financial_year_end) {
      newErrors.financial_year_end = 'Financial year end is required';
    }

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    try {
      await createProject.mutateAsync(formData);
      // Success - close dialog and reset form
      onOpenChange(false);
      setFormData({
        project_name: '',
        client_id: 0,
        jurisdiction: 'HK',
        currency: 'HKD',
        financial_year_end: new Date().toISOString().split('T')[0],
        entity_type: '',
        description: '',
      });
      setErrors({});
      setShowNewClientForm(false);
      setNewClientName('');
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
          <DialogDescription>
            Add a new audit project. Fill in the required information below.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-6 py-4">
            {/* Project Name */}
            <div className="grid gap-2">
              <Label htmlFor="project_name">
                Project Name <span className="text-red-500">*</span>
              </Label>
              <Input
                id="project_name"
                value={formData.project_name}
                onChange={(e) =>
                  setFormData({ ...formData, project_name: e.target.value })
                }
                placeholder="e.g., ABC Company Ltd - FY2024 Audit"
                className={errors.project_name ? 'border-red-500' : ''}
              />
              {errors.project_name && (
                <p className="text-sm text-red-500">{errors.project_name}</p>
              )}
            </div>

            {/* Client Selection */}
            <div className="grid gap-2">
              <Label htmlFor="client">
                Client <span className="text-red-500">*</span>
              </Label>

              {clients.length === 0 && !showNewClientForm && (
                <Alert>
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    No clients found. Please create a client first.
                  </AlertDescription>
                </Alert>
              )}

              {!showNewClientForm && clients.length > 0 && (
                <Select
                  value={formData.client_id ? String(formData.client_id) : ''}
                  onValueChange={(value) =>
                    setFormData({ ...formData, client_id: parseInt(value) })
                  }
                >
                  <SelectTrigger className={errors.client ? 'border-red-500' : ''}>
                    <SelectValue placeholder="Select a client" />
                  </SelectTrigger>
                  <SelectContent>
                    {clients.map((client) => (
                      <SelectItem key={client.id} value={String(client.id)}>
                        {client.company_name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}

              {showNewClientForm && (
                <div className="flex gap-2">
                  <Input
                    placeholder="Company name"
                    value={newClientName}
                    onChange={(e) => setNewClientName(e.target.value)}
                    className={errors.client ? 'border-red-500' : ''}
                  />
                  <Button
                    type="button"
                    onClick={handleCreateClient}
                    disabled={createClient.isPending}
                  >
                    {createClient.isPending ? 'Creating...' : 'Add'}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => {
                      setShowNewClientForm(false);
                      setNewClientName('');
                      setErrors({ ...errors, client: '' });
                    }}
                  >
                    Cancel
                  </Button>
                </div>
              )}

              {!showNewClientForm && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setShowNewClientForm(true)}
                  className="w-fit"
                >
                  + Create New Client
                </Button>
              )}

              {errors.client && (
                <p className="text-sm text-red-500">{errors.client}</p>
              )}
            </div>

            {/* Jurisdiction */}
            <div className="grid gap-2">
              <Label htmlFor="jurisdiction">
                Jurisdiction <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.jurisdiction}
                onValueChange={(value: Jurisdiction) =>
                  setFormData({ ...formData, jurisdiction: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="HK">Hong Kong</SelectItem>
                  <SelectItem value="SG">Singapore</SelectItem>
                  <SelectItem value="AU">Australia</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Currency */}
            <div className="grid gap-2">
              <Label htmlFor="currency">
                Currency <span className="text-red-500">*</span>
              </Label>
              <Select
                value={formData.currency}
                onValueChange={(value: Currency) =>
                  setFormData({ ...formData, currency: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="HKD">HKD - Hong Kong Dollar</SelectItem>
                  <SelectItem value="SGD">SGD - Singapore Dollar</SelectItem>
                  <SelectItem value="AUD">AUD - Australian Dollar</SelectItem>
                  <SelectItem value="USD">USD - US Dollar</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Financial Year End */}
            <div className="grid gap-2">
              <Label htmlFor="financial_year_end">
                Financial Year End <span className="text-red-500">*</span>
              </Label>
              <Input
                id="financial_year_end"
                type="date"
                value={formData.financial_year_end}
                onChange={(e) =>
                  setFormData({ ...formData, financial_year_end: e.target.value })
                }
                className={errors.financial_year_end ? 'border-red-500' : ''}
              />
              {errors.financial_year_end && (
                <p className="text-sm text-red-500">{errors.financial_year_end}</p>
              )}
            </div>

            {/* Entity Type (Optional) */}
            <div className="grid gap-2">
              <Label htmlFor="entity_type">Entity Type</Label>
              <Input
                id="entity_type"
                value={formData.entity_type}
                onChange={(e) =>
                  setFormData({ ...formData, entity_type: e.target.value })
                }
                placeholder="e.g., Private Limited Company"
              />
            </div>

            {/* Description (Optional) */}
            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                placeholder="Additional notes or description"
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createProject.isPending}>
              {createProject.isPending ? 'Creating...' : 'Create Project'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
