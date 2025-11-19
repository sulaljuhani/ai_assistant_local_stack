/**
 * Input Validation Utility for n8n Webhooks
 *
 * Usage: Add this as a Code node at the start of webhook workflows
 *
 * Copy this entire code into a Code node in n8n, then customize
 * the schema object for your specific webhook requirements.
 */

/**
 * Validate input data against a schema
 * @param {object} data - The data to validate
 * @param {object} schema - Schema definition
 * @returns {object} - { valid: boolean, errors: string[], data: object }
 */
function validateInput(data, schema) {
  const errors = [];
  const sanitized = {};

  for (const [field, rules] of Object.entries(schema)) {
    const value = data[field];

    // Check required fields
    if (rules.required && (value === undefined || value === null || value === '')) {
      errors.push(`Missing required field: ${field}`);
      continue;
    }

    // Skip validation if field is optional and not provided
    if (!rules.required && (value === undefined || value === null)) {
      sanitized[field] = rules.default !== undefined ? rules.default : null;
      continue;
    }

    // Type validation
    if (rules.type) {
      const actualType = Array.isArray(value) ? 'array' : typeof value;

      if (actualType !== rules.type) {
        errors.push(`Field '${field}' must be ${rules.type}, got ${actualType}`);
        continue;
      }
    }

    // String validations
    if (rules.type === 'string') {
      if (rules.minLength && value.length < rules.minLength) {
        errors.push(`Field '${field}' must be at least ${rules.minLength} characters`);
      }

      if (rules.maxLength && value.length > rules.maxLength) {
        errors.push(`Field '${field}' exceeds maximum length of ${rules.maxLength} characters`);
      }

      if (rules.pattern && !new RegExp(rules.pattern).test(value)) {
        errors.push(`Field '${field}' does not match required pattern`);
      }

      if (rules.enum && !rules.enum.includes(value)) {
        errors.push(`Field '${field}' must be one of: ${rules.enum.join(', ')}`);
      }

      // Sanitize: trim whitespace
      sanitized[field] = value.trim();
    }

    // Number validations
    else if (rules.type === 'number') {
      const num = Number(value);

      if (isNaN(num)) {
        errors.push(`Field '${field}' must be a valid number`);
        continue;
      }

      if (rules.min !== undefined && num < rules.min) {
        errors.push(`Field '${field}' must be at least ${rules.min}`);
      }

      if (rules.max !== undefined && num > rules.max) {
        errors.push(`Field '${field}' must be at most ${rules.max}`);
      }

      sanitized[field] = num;
    }

    // Boolean validations
    else if (rules.type === 'boolean') {
      // Convert string booleans
      if (typeof value === 'string') {
        sanitized[field] = value.toLowerCase() === 'true';
      } else {
        sanitized[field] = Boolean(value);
      }
    }

    // Array validations
    else if (rules.type === 'array') {
      if (rules.minItems && value.length < rules.minItems) {
        errors.push(`Field '${field}' must have at least ${rules.minItems} items`);
      }

      if (rules.maxItems && value.length > rules.maxItems) {
        errors.push(`Field '${field}' must have at most ${rules.maxItems} items`);
      }

      sanitized[field] = value;
    }

    // Object type
    else if (rules.type === 'object') {
      sanitized[field] = value;
    }

    // Date/datetime validation
    else if (rules.type === 'datetime') {
      const date = new Date(value);
      if (isNaN(date.getTime())) {
        errors.push(`Field '${field}' must be a valid datetime`);
      } else {
        sanitized[field] = date.toISOString();
      }
    }

    // UUID validation
    else if (rules.type === 'uuid') {
      const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      if (!uuidPattern.test(value)) {
        errors.push(`Field '${field}' must be a valid UUID`);
      } else {
        sanitized[field] = value;
      }
    }

    // Custom validator function
    else if (rules.validator && typeof rules.validator === 'function') {
      const validationResult = rules.validator(value);
      if (validationResult !== true) {
        errors.push(validationResult || `Field '${field}' failed custom validation`);
      } else {
        sanitized[field] = value;
      }
    }

    // No special handling, just copy
    else {
      sanitized[field] = value;
    }
  }

  return {
    valid: errors.length === 0,
    errors: errors,
    data: sanitized
  };
}

// ============================================================================
// EXAMPLE SCHEMAS - Customize for your workflow
// ============================================================================

// Example 1: Create Reminder Schema
const createReminderSchema = {
  title: {
    type: 'string',
    required: true,
    minLength: 1,
    maxLength: 200
  },
  reminder_time: {
    type: 'datetime',
    required: true
  },
  description: {
    type: 'string',
    required: false,
    maxLength: 1000
  },
  priority: {
    type: 'number',
    required: false,
    min: 0,
    max: 3,
    default: 1
  },
  recurrence: {
    type: 'string',
    required: false,
    enum: ['none', 'daily', 'weekly', 'monthly', 'yearly'],
    default: 'none'
  }
};

// Example 2: Create Task Schema
const createTaskSchema = {
  title: {
    type: 'string',
    required: true,
    minLength: 1,
    maxLength: 200
  },
  description: {
    type: 'string',
    required: false,
    maxLength: 5000
  },
  due_date: {
    type: 'datetime',
    required: false
  },
  priority: {
    type: 'number',
    required: false,
    min: 1,
    max: 5,
    default: 3
  },
  status: {
    type: 'string',
    required: false,
    enum: ['todo', 'in_progress', 'waiting', 'done', 'cancelled'],
    default: 'todo'
  }
};

// Example 3: Store Memory Schema
const storeMemorySchema = {
  content: {
    type: 'string',
    required: true,
    minLength: 1,
    maxLength: 10000
  },
  conversation_id: {
    type: 'string',
    required: false
  },
  conversation_title: {
    type: 'string',
    required: false,
    maxLength: 200,
    default: 'Untitled Conversation'
  },
  source: {
    type: 'string',
    required: false,
    enum: ['chat', 'chatgpt', 'claude', 'gemini', 'anythingllm'],
    default: 'chat'
  },
  salience_score: {
    type: 'number',
    required: false,
    min: 0.0,
    max: 1.0,
    default: 0.5
  }
};

// Example 4: Search Query Schema
const searchSchema = {
  query: {
    type: 'string',
    required: true,
    minLength: 1,
    maxLength: 500
  },
  sector: {
    type: 'string',
    required: false,
    enum: ['semantic', 'episodic', 'procedural', 'emotional', 'reflective']
  },
  limit: {
    type: 'number',
    required: false,
    min: 1,
    max: 100,
    default: 10
  },
  summarize: {
    type: 'boolean',
    required: false,
    default: false
  }
};

// ============================================================================
// USAGE IN N8N WORKFLOW
// ============================================================================

// Get input from webhook
const input = $json.body || $json;

// Choose your schema (change this based on your workflow)
const schema = createReminderSchema;  // <-- CHANGE THIS

// Validate
const validation = validateInput(input, schema);

if (!validation.valid) {
  // Return error response
  return [{
    json: {
      success: false,
      error: 'Input validation failed',
      errors: validation.errors
    }
  }];
}

// Return sanitized data for next node
return [{
  json: {
    success: true,
    data: validation.data
  }
}];

// ============================================================================
// NOTES
// ============================================================================
/**
 * In your n8n workflow:
 *
 * 1. Add a Code node right after the Webhook node
 * 2. Copy this entire file into the Code node
 * 3. Change the schema constant to match your webhook (line 227)
 * 4. Add an IF node after the Code node to check validation.valid
 * 5. If false, respond with errors using respondToWebhook
 * 6. If true, continue with your workflow logic
 *
 * Example workflow structure:
 *
 * Webhook → Code (Validation) → IF → [False] → Respond Error
 *                                  ↓
 *                               [True] → Continue processing...
 */
