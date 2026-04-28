package tools

import (
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

// AddOrganizationTools registers all organization tools with the server.
func AddOrganizationTools(s *server.MCPServer) {
	ListOrganizations.Register(s)
}
