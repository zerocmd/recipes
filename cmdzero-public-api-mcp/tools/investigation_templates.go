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

// ListInvestigationTemplatesParams defines the parameters for listing investigation templates.
type ListInvestigationTemplatesParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression to narrow results"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func listInvestigationTemplates(ctx context.Context, args ListInvestigationTemplatesParams) (json.RawMessage, error) {
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

	path := "/investigation-templates"
	if len(params) > 0 {
		path += "?" + params.Encode()
	}

	return c.Get(ctx, path)
}

var ListInvestigationTemplates = mcpcmdzero.MustTool(
	"list_investigation_templates",
	"List investigation templates available to the organization. Templates define pre-configured investigation workflows with specific lead types, default settings, and automated questions. Use template IDs when starting investigations.",
	listInvestigationTemplates,
	mcp.WithTitleAnnotation("List investigation templates"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// GetInvestigationTemplateParams defines the parameters for retrieving a single template.
type GetInvestigationTemplateParams struct {
	TemplateID string `json:"templateId" jsonschema:"required,description=The unique identifier of the investigation template"`
}

func getInvestigationTemplate(ctx context.Context, args GetInvestigationTemplateParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.Get(ctx, "/investigation-templates/"+args.TemplateID)
}

var GetInvestigationTemplate = mcpcmdzero.MustTool(
	"get_investigation_template",
	"Retrieve details for a specific investigation template, including its lead types, default settings, scenario, severity, and sensitivity configuration.",
	getInvestigationTemplate,
	mcp.WithTitleAnnotation("Get investigation template"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// QueryInvestigationTemplatesParams defines the parameters for querying investigation templates via HTTP QUERY.
type QueryInvestigationTemplatesParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func queryInvestigationTemplates(ctx context.Context, args QueryInvestigationTemplatesParams) (json.RawMessage, error) {
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

	return c.Query(ctx, "/investigation-templates", bytes.NewReader(body))
}

var QueryInvestigationTemplates = mcpcmdzero.MustTool(
	"query_investigation_templates",
	"Query investigation templates via HTTP QUERY (POST-shaped request body) for filters too long to fit in a URL. Same fields and pagination semantics as list_investigation_templates.",
	queryInvestigationTemplates,
	mcp.WithTitleAnnotation("Query investigation templates"),
	mcp.WithReadOnlyHintAnnotation(true),
)

// AddInvestigationTemplateTools registers all investigation template tools with the server.
func AddInvestigationTemplateTools(s *server.MCPServer) {
	ListInvestigationTemplates.Register(s)
	QueryInvestigationTemplates.Register(s)
	GetInvestigationTemplate.Register(s)
}
