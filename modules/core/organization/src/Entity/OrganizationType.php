<?php

declare(strict_types=1);

namespace Drupal\organization\Entity;

use Drupal\Core\Config\Entity\ConfigEntityBundleBase;
use Drupal\Core\Entity\Attribute\ConfigEntityType;
use Drupal\Core\Entity\EntityDeleteForm;
use Drupal\Core\Entity\EntityViewBuilder;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\entity\Routing\DefaultHtmlRouteProvider;
use Drupal\organization\Form\OrganizationTypeForm;
use Drupal\organization\OrganizationTypeListBuilder;

/**
 * Defines the organization type entity.
 */
#[ConfigEntityType(
  id: 'organization_type',
  label: new TranslatableMarkup('Organization type'),
  label_collection: new TranslatableMarkup('Organization types'),
  label_singular: new TranslatableMarkup('Organization type'),
  label_plural: new TranslatableMarkup('Organization types'),
  config_prefix: 'type',
  entity_keys: [
    'id' => 'id',
    'label' => 'label',
    'uuid' => 'uuid',
  ],
  handlers: [
    'list_builder' => OrganizationTypeListBuilder::class,
    'view_builder' => EntityViewBuilder::class,
    'form' => [
      'add' => OrganizationTypeForm::class,
      'edit' => OrganizationTypeForm::class,
      'delete' => EntityDeleteForm::class,
    ],
    'route_provider' => [
      'default' => DefaultHtmlRouteProvider::class,
    ],
  ],
  links: [
    'canonical' => '/admin/structure/organization-type/{organization_type}',
    'add-form' => '/admin/structure/organization-type/add',
    'edit-form' => '/admin/structure/organization-type/{organization_type}/edit',
    'delete-form' => '/admin/structure/organization-type/{organization_type}/delete',
    'collection' => '/admin/structure/organization-type',
  ],
  admin_permission: 'administer organization types',
  bundle_of: 'organization',
  label_count: [
    'singular' => '@count organization type',
    'plural' => '@count organization types',
  ],
  config_export: [
    'id', 'label',
    'description',
    'new_revision',
  ],
)]
class OrganizationType extends ConfigEntityBundleBase implements OrganizationTypeInterface {

  /**
   * The organization type ID.
   *
   * @var string
   */
  protected $id;

  /**
   * The organization type label.
   *
   * @var string
   */
  protected $label;

  /**
   * A brief description of this organization type.
   *
   * @var string
   */
  protected $description;

  /**
   * Default value of the 'Create new revision' checkbox.
   *
   * @var bool
   */
  protected $new_revision = TRUE;

  /**
   * {@inheritdoc}
   */
  public function getDescription() {
    return $this->description;
  }

  /**
   * {@inheritdoc}
   */
  public function setDescription($description) {
    return $this->set('description', $description);
  }

  /**
   * {@inheritdoc}
   */
  public function shouldCreateNewRevision() {
    return $this->new_revision;
  }

  /**
   * {@inheritdoc}
   */
  public function setNewRevision($new_revision) {
    return $this->set('new_revision', $new_revision);
  }

}
