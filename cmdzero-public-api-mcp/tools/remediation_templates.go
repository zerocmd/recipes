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

// ListRemediationTemplatesParams defines the parameters for listing remediation templates.
type ListRemediationTemplatesParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression to narrow results (e.g. contains(name\\, 'Disable'))"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func listRemediationTemplates(ctx context.Context, args ListRemediationTemplatesParams) (json.RawMessage, error) {
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

	path := "/remediation-templates"
	if len(params) > 0 {
		path += "?" + params.Encode()
	}

	return c.Get(ctx, path)
}

var ListRemediationTemplates = mcpcmdzero.MustTool(
	"list_remediation_templates",
	"List remediation templates available to the organization. Templates are determined by active integrations and their capabilities. Each template defines a remediation action (e.g. disable user, revoke session) and the subject type it operates on.",
	listRemediationTemplates,
	mcp.WithTitleAnnotation("List remediation templates"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// GetRemediationTemplateParams defines the parameters for retrieving a single remediation template.
type GetRemediationTemplateParams struct {
	TemplateID string `json:"templateId" jsonschema:"required,description=The unique identifier of the remediation template"`
}

func getRemediationTemplate(ctx context.Context, args GetRemediationTemplateParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.Get(ctx, "/remediation-templates/"+args.TemplateID)
}

var GetRemediationTemplate = mcpcmdzero.MustTool(
	"get_remediation_template",
	"Retrieve details for a specific remediation template, including its name, description, subject type, and whether an undo template is available.",
	getRemediationTemplate,
	mcp.WithTitleAnnotation("Get remediation template"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// QueryRemediationTemplatesParams defines the parameters for querying remediation templates via HTTP QUERY.
type QueryRemediationTemplatesParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func queryRemediationTemplates(ctx context.Context, args QueryRemediationTemplatesParams) (json.RawMessage, error) {
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

	return c.Query(ctx, "/remediation-templates", bytes.NewReader(body))
}

var QueryRemediationTemplates = mcpcmdzero.MustTool(
	"query_remediation_templates",
	"Query remediation templates via HTTP QUERY (POST-shaped request body) for filters too long to fit in a URL. Same fields and pagination semantics as list_remediation_templates.",
	queryRemediationTemplates,
	mcp.WithTitleAnnotation("Query remediation templates"),
	mcp.WithReadOnlyHintAnnotation(true),
)

// AddRemediationTemplateTools registers all remediation template tools with the server.
func AddRemediationTemplateTools(s *server.MCPServer) {
	ListRemediationTemplates.Register(s)
	QueryRemediationTemplates.Register(s)
	GetRemediationTemplate.Register(s)
}
