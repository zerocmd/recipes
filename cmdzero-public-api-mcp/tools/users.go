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

// ListUsersParams defines the parameters for listing users.
type ListUsersParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression (e.g. role ne 'observer' to find assignable users\\, contains(name\\, 'Kim'))"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response to retrieve the next page"`
}

func listUsers(ctx context.Context, args ListUsersParams) (json.RawMessage, error) {
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

	path := "/users"
	if len(params) > 0 {
		path += "?" + params.Encode()
	}

	return c.Get(ctx, path)
}

var ListUsers = mcpcmdzero.MustTool(
	"list_users",
	"List users in the organization. Use filter \"role ne 'observer'\" to find users who can be assigned to investigations. Results are sorted by name.",
	listUsers,
	mcp.WithTitleAnnotation("List users"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// GetUserParams defines the parameters for retrieving a single user.
type GetUserParams struct {
	UserID string `json:"userId" jsonschema:"required,description=The unique identifier of the user (UUID)"`
}

func getUser(ctx context.Context, args GetUserParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.Get(ctx, "/users/"+args.UserID)
}

var GetUser = mcpcmdzero.MustTool(
	"get_user",
	"Retrieve details for a specific user in the organization, including their name, email, role, and audit information.",
	getUser,
	mcp.WithTitleAnnotation("Get user"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// QueryUsersParams defines the parameters for querying users via HTTP QUERY.
type QueryUsersParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression (e.g. role ne 'observer'\\, contains(name\\, 'Kim'))"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func queryUsers(ctx context.Context, args QueryUsersParams) (json.RawMessage, error) {
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

	return c.Query(ctx, "/users", bytes.NewReader(body))
}

var QueryUsers = mcpcmdzero.MustTool(
	"query_users",
	"Query users via HTTP QUERY (POST-shaped request body) for filters too long to fit in a URL. Same fields and pagination semantics as list_users.",
	queryUsers,
	mcp.WithTitleAnnotation("Query users"),
	mcp.WithReadOnlyHintAnnotation(true),
)

// AddUserTools registers all user tools with the server.
func AddUserTools(s *server.MCPServer) {
	ListUsers.Register(s)
	QueryUsers.Register(s)
	GetUser.Register(s)
}
