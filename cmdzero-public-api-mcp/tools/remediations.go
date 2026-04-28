package tools

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/url"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	mcpcmdzero "github.com/cmdzero/cmdzero-public-api-mcp"
)

// ListRemediationsParams defines the parameters for listing remediations.
type ListRemediationsParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression to narrow results (e.g. status eq 'success'\\, contains(templateName\\, 'Disable'))"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func listRemediations(ctx context.Context, args ListRemediationsParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	params := url.Values{}
	if args.Filter != "" {
		params.Set("filter", args.Filter)
	}
	if args.Limit > 0 {
		params.Set("limit", fmt.Sprintf("%d", args.Limit))
	}
	if args.Next != "" {
		params.Set("next", args.Next)
	}

	path := "/remediations"
	if len(params) > 0 {
		path += "?" + params.Encode()
	}

	return c.Get(ctx, path)
}

var ListRemediations = mcpcmdzero.MustTool(
	"list_remediations",
	"List remediations for the organization. Results are sorted by creation time (newest first). Supports filtering by status, subject type, and template name.",
	listRemediations,
	mcp.WithTitleAnnotation("List remediations"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// QueryRemediationsParams defines the parameters for querying remediations via HTTP QUERY.
type QueryRemediationsParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func queryRemediations(ctx context.Context, args QueryRemediationsParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	payload := make(map[string]any)
	if args.Filter != "" {
		payload["filter"] = args.Filter
	}
	if args.Limit > 0 {
		payload["limit"] = args.Limit
	}
	if args.Next != "" {
		payload["next"] = args.Next
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	return c.Query(ctx, "/remediations", bytes.NewReader(body))
}

var QueryRemediations = mcpcmdzero.MustTool(
	"query_remediations",
	"Query remediations via HTTP QUERY (POST-shaped request body) for filters too long to fit in a URL. Same fields and pagination semantics as list_remediations.",
	queryRemediations,
	mcp.WithTitleAnnotation("Query remediations"),
	mcp.WithReadOnlyHintAnnotation(true),
)

// RemediationSubject represents the entity to remediate.
type RemediationSubject struct {
	Type  string `json:"type" jsonschema:"required,description=Subject type (must match the template's subjectType\\, e.g. MICROSOFT_ENTRA_USER_PRINCIPAL_NAME\\, AWS_IAM_USER)"`
	Value string `json:"value" jsonschema:"required,description=Subject value (e.g. jmaldive@example.com\\, arn:aws:iam::123456:user/admin)"`
}

// CreateRemediationParams defines the parameters for creating a remediation.
type CreateRemediationParams struct {
	TemplateID    string             `json:"templateId" jsonschema:"required,description=Remediation template ID defining the action to execute"`
	Subject       RemediationSubject `json:"subject" jsonschema:"required,description=The entity to remediate (type must match template's subjectType)"`
	Justification string             `json:"justification,omitempty" jsonschema:"description=Reason for executing this remediation action (optional but recommended for audit trail)"`
	Postback      *PostbackConfig    `json:"postback,omitempty" jsonschema:"description=Postback URL configuration to receive notification when remediation completes"`
}

func createRemediation(ctx context.Context, args CreateRemediationParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	payload := map[string]any{
		"templateId": args.TemplateID,
		"subject":    args.Subject,
	}
	if args.Justification != "" {
		payload["justification"] = args.Justification
	}
	if args.Postback != nil {
		payload["postback"] = args.Postback
	}

	body, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}

	return c.Post(ctx, "/remediations", bytes.NewReader(body))
}

var CreateRemediation = mcpcmdzero.MustTool(
	"create_remediation",
	"Execute a remediation action against a subject. The template must be available to the organization and the subject type must match the template's subjectType. The remediation is queued for execution and its status can be monitored with get_remediation.",
	createRemediation,
	mcp.WithTitleAnnotation("Create remediation"),
)

// GetRemediationParams defines the parameters for retrieving a single remediation.
type GetRemediationParams struct {
	RemediationID string `json:"remediationId" jsonschema:"required,description=The unique identifier of the remediation (UUID)"`
}

func getRemediation(ctx context.Context, args GetRemediationParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.Get(ctx, "/remediations/"+args.RemediationID)
}

var GetRemediation = mcpcmdzero.MustTool(
	"get_remediation",
	"Retrieve a remediation by ID, including its current execution status, subject, template used, justification, and result details.",
	getRemediation,
	mcp.WithTitleAnnotation("Get remediation"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// AddRemediationTools registers all remediation tools with the server.
func AddRemediationTools(s *server.MCPServer) {
	AddRemediationTemplateTools(s)
	ListRemediations.Register(s)
	QueryRemediations.Register(s)
	CreateRemediation.Register(s)
	GetRemediation.Register(s)
}
