<?php

declare(strict_types=1);

namespace Drupal\farm_geo;

/**
 * An object that wraps the GeoPHP Geometry with additional properties.
 *
 * As suggested by the GeoPHP maintainer:
 *
 * @see https://github.com/phayes/geoPHP/issues/25#issuecomment-5576661
 * @see https://github.com/phayes/geoPHP/pull/41#issuecomment-6983505
 */
class GeometryWrapper {

  public function __construct(
    public \Geometry $geometry,
    public array $properties = [],
  ) {}

}
