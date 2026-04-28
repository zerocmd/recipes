package tools

import (
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
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 100\\, min 1\\, max 100)"`
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

// AddInvestigationTemplateTools registers all investigation template tools with the server.
func AddInvestigationTemplateTools(s *server.MCPServer) {
	ListInvestigationTemplates.Register(s)
	GetInvestigationTemplate.Register(s)
}
