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

// ListCatalogTypesParams defines the parameters for listing catalog types.
type ListCatalogTypesParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression to narrow results"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func listCatalogTypes(ctx context.Context, args ListCatalogTypesParams) (json.RawMessage, error) {
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

	path := "/catalog/types"
	if len(params) > 0 {
		path += "?" + params.Encode()
	}

	return c.Get(ctx, path)
}

var ListCatalogTypes = mcpcmdzero.MustTool(
	"list_catalog_types",
	"List catalog types available in the organization. Catalog types define alert schemas and data structures that Command Zero understands. Use catalog type IDs as alertSchema values when starting investigations.",
	listCatalogTypes,
	mcp.WithTitleAnnotation("List catalog types"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// GetCatalogTypeParams defines the parameters for retrieving a single catalog type.
type GetCatalogTypeParams struct {
	TypeID string `json:"typeId" jsonschema:"required,description=The unique identifier of the catalog type"`
}

func getCatalogType(ctx context.Context, args GetCatalogTypeParams) (json.RawMessage, error) {
	c := mcpcmdzero.CmdZeroClientFromContext(ctx)
	if c == nil {
		return nil, fmt.Errorf("cmdzero client not configured")
	}

	return c.Get(ctx, "/catalog/types/"+args.TypeID)
}

var GetCatalogType = mcpcmdzero.MustTool(
	"get_catalog_type",
	"Retrieve details for a specific catalog type, including its schema definition, field mappings, and supported data types.",
	getCatalogType,
	mcp.WithTitleAnnotation("Get catalog type"),
	mcp.WithIdempotentHintAnnotation(true),
	mcp.WithReadOnlyHintAnnotation(true),
)

// QueryCatalogTypesParams defines the parameters for querying catalog types via HTTP QUERY.
type QueryCatalogTypesParams struct {
	Filter string `json:"filter,omitempty" jsonschema:"description=OData filter expression"`
	Limit  int    `json:"limit,omitempty" jsonschema:"description=Maximum number of items to return (default 10000\\, min 1\\, max 10000)"`
	Next   string `json:"next,omitempty" jsonschema:"description=Pagination cursor from a previous response"`
}

func queryCatalogTypes(ctx context.Context, args QueryCatalogTypesParams) (json.RawMessage, error) {
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

	return c.Query(ctx, "/catalog/types", bytes.NewReader(body))
}

var QueryCatalogTypes = mcpcmdzero.MustTool(
	"query_catalog_types",
	"Query catalog types via HTTP QUERY (POST-shaped request body) for filters too long to fit in a URL. Same fields and pagination semantics as list_catalog_types.",
	queryCatalogTypes,
	mcp.WithTitleAnnotation("Query catalog types"),
	mcp.WithReadOnlyHintAnnotation(true),
)

// AddCatalogTools registers all catalog tools with the server.
func AddCatalogTools(s *server.MCPServer) {
	ListCatalogTypes.Register(s)
	QueryCatalogTypes.Register(s)
	GetCatalogType.Register(s)
}
