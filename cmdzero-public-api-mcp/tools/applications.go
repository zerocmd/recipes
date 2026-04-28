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

// ListApplicationsParams defines the parameters for listing applications.
type ListApplicationsParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression to narrow results (e.g. contains(name\\, 'SIEM'))"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 100\\, min 1\\, max 100)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response to retrieve the next page"`
}

func listApplications(ctx context.Context, args ListApplicationsParams) (json.RawMessage, error) {
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

	path := "/applications"
	if len(params) > 0 {
		path += "?" + params.Encode()
	}

	return c.Get(ctx, path)
}

var ListApplications = mcpcmdzero.MustTool(
	"list_applications",
	"List applications in the organization. Applications represent API integrations configured by administrators. Results are sorted by name.",
	listApplications,
	mcp.WithTitleAnnotation("List applications"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// GetApplicationParams defines the parameters for retrieving a single application.
type GetApplicationParams struct {
	ApplicationID string `json:"applicationId" jsonschema:"required,description=The unique identifier of the application (UUID)"`
}

func getApplication(ctx context.Context, args GetApplicationParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.Get(ctx, "/applications/"+args.ApplicationID)
}

var GetApplication = mcpcmdzero.MustTool(
	"get_application",
	"Retrieve details for a specific application in the organization, including its name, role, fingerprint, and audit information.",
	getApplication,
	mcp.WithTitleAnnotation("Get application"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// AddApplicationTools registers all application tools with the server.
func AddApplicationTools(s *server.MCPServer) {
	ListApplications.Register(s)
	GetApplication.Register(s)
}
