package tools

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	mcpcmdzero "github.com/cmdzero/cmdzero-public-api-mcp"
)

// ListOrganizationsParams defines the parameters for listing organizations (none required).
type ListOrganizationsParams struct{}

func listOrganizations(ctx context.Context, _ ListOrganizationsParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.GetGlobal(ctx, "/organizations")
}

var ListOrganizations = mcpcmdzero.MustTool(
	"list_organizations",
	"List organizations accessible to the authenticated application. Returns organization details and the application's role in each organization.",
	listOrganizations,
	mcp.WithTitleAnnotation("List organizations"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// QueryOrganizationsParams defines the parameters for querying organizations via HTTP QUERY.
type QueryOrganizationsParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression (e.g. role eq 'Investigators')"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func queryOrganizations(ctx context.Context, args QueryOrganizationsParams) (json.RawMessage, error) {
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

	return c.QueryGlobal(ctx, "/organizations", bytes.NewReader(body))
}

var QueryOrganizations = mcpcmdzero.MustTool(
	"query_organizations",
	"Query organizations via HTTP QUERY (POST-shaped request body) for filters too long to fit in a URL. Same fields and pagination semantics as list_organizations.",
	queryOrganizations,
	mcp.WithTitleAnnotation("Query organizations"),
	mcp.WithReadOnlyHintAnnotation(true),
)

// AddOrganizationTools registers all organization tools with the server.
func AddOrganizationTools(s *server.MCPServer) {
	ListOrganizations.Register(s)
	QueryOrganizations.Register(s)
}
